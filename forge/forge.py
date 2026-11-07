"""Asset Forge factory core: author .model files, assemble them, export GLB, render previews/sprites.

Asset Forge itself has no CLI, so this module re-implements the parts of it we need
(using the block meshes extracted into Library/ by extract_library.py):

  * .model read/write          - byte-compatible with Asset Forge 2.5.x (files open in the app)
  * assembly                   - Unity TRS transforms, per-slot materials, AF box-UV texturing
  * GLB export                 - same axis convention as Asset Forge's own export (Z reversed;
                                 model front faces -Z, +Y up, 1 unit = 1 m at scale 100)
  * software renderer          - previews, contact sheets, crisp pixel-art sprites

Python authoring:

    from forge import Model
    m = Model()
    m.mat("paint", "#E04848")
    m.add("Vehicles/body_standard", (0, 0, 0), recolor={"metalGreen": "paint"})
    m.save("Assets/_wip/car.model")
    m.export_glb("Assets/_wip/car.glb")
    m.render("Assets/_wip/car_preview.png", view="iso")

CLI: see `python forge/forge.py -h`.
"""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
AF = ROOT / "Asset Forge 2.5.3 (Windows)"
AF_TEXTURES = AF / "Textures"
LIB = ROOT / "Library"

_LIB_CACHE: dict | None = None
_MESH_CACHE: dict = {}
_TEX_CACHE: dict = {}


# ------------------------------------------------------------------ library

def library() -> dict:
    global _LIB_CACHE
    if _LIB_CACHE is None:
        data = json.loads((LIB / "library.json").read_text())
        _LIB_CACHE = {
            "blocks": {f"{b['collection']}/{b['type']}": b for b in data["blocks"]},
            "materials": data["materials"],
        }
    return _LIB_CACHE


def block_info(key: str) -> dict:
    lib = library()["blocks"]
    if key not in lib:
        close = [k for k in lib if key.split("/")[-1].lower() in k.lower()][:10]
        raise KeyError(f"unknown block {key!r}; similar: {close}")
    return lib[key]


def find(pattern: str, collection: str | None = None, deluxe: bool = False) -> list[str]:
    """Regex search over 'Collection/type' keys."""
    rx = re.compile(pattern, re.I)
    return [k for k, b in library()["blocks"].items()
            if rx.search(k) and (collection is None or b["collection"] == collection)
            and (deluxe or not b["deluxe"])]


def load_mesh(key: str):
    if key not in _MESH_CACHE:
        b = block_info(key)
        d = np.load(LIB / "blocks" / b["collection"] / f"{b['type'].replace('%', '_pct_')}.npz")
        tris = [d[f"tris_{i}"] for i in range(sum(1 for k in d.files if k.startswith("tris_")))]
        _MESH_CACHE[key] = (d["positions"], d["normals"], d["uvs"], tris)
    return _MESH_CACHE[key]


# ------------------------------------------------------------------ colors

def hex_to_rgba(h: str) -> list[float]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    vals = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
    return vals + [1.0] * (4 - len(vals))


def rgba_to_hex(c) -> str:
    return "#" + "".join(f"{round(max(0, min(1, v)) * 255):02X}" for v in c[:3])


def srgb_to_linear(c):
    c = np.asarray(c, np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ------------------------------------------------------------------ model data

@dataclass
class Material:
    name: str
    color: list = field(default_factory=lambda: [1, 1, 1, 1])
    texture: str | None = None  # "<AF texture folder>/<file>" e.g. "32px Microart/tex_Micro12.png"
    scale: tuple = (1.0, 1.0)
    shader: str = "Default"
    mapping: int = 0           # 1 = keep the mesh's own UVs instead of box mapping
    value_a: float = 0.25      # Default shader: metallic
    value_b: float = 0.25      # Default shader: glossiness

    def to_line(self) -> str:
        c = self.color
        s = f"[name:{self.name};color:RGBA({c[0]:.3f}, {c[1]:.3f}, {c[2]:.3f}, {c[3]:.3f});"
        s += f"scale:({self.scale[0]:.1f}, {self.scale[1]:.1f});"
        if self.texture:
            s += f"texture:{self.texture};"
        s += f"shader:{self.shader};mapping:{self.mapping};"
        if self.shader in ("Default", "Gradient"):
            s += f"valueA:{self.value_a:g};valueB:{self.value_b:g};"
        return s + "]"


@dataclass
class Part:
    block: str                      # "Collection/type"
    position: tuple = (0.0, 0.0, 0.0)
    rotation: tuple = (0.0, 0.0, 0.0)  # Unity euler degrees (applied Z, X, Y)
    scale: tuple = (1.0, 1.0, 1.0)
    materials: list = field(default_factory=list)  # material name per mesh slot
    group: str = ""
    name: str = ""
    locked: bool = False
    hidden: bool = False

    def to_line(self) -> str:
        col, typ = self.block.split("/", 1)
        v = lambda t: "(" + ", ".join(f"{x:.4f}" for x in t) + ")"
        return (f"[name:{self.name};collection:{col};type:{typ};position:{v(self.position)};"
                f"rotation:{v(tuple(r % 360 for r in self.rotation))};scale:{v(self.scale)};"
                f"group:{self.group};locked:{self.locked};hidden:{self.hidden};"
                f"materials:{'+'.join(self.materials)};]")


class Model:
    """An Asset Forge model: named materials + placed blocks."""

    def __init__(self):
        self.materials: dict[str, Material] = {}
        self.parts: list[Part] = []

    # ---- authoring
    def mat(self, name, color="#FFFFFF", texture=None, scale=1.0, metallic=0.0, gloss=0.25, mapping=0):
        """Define/override a material. color: hex or RGBA list. texture: AF texture ref or path."""
        rgba = hex_to_rgba(color) if isinstance(color, str) else list(color) + [1.0] * (4 - len(color))
        if texture:
            texture = texture_ref(texture)
        sc = (scale, scale) if isinstance(scale, (int, float)) else tuple(scale)
        self.materials[name] = Material(name, rgba, texture, sc, "Default", mapping, metallic, gloss)
        return name

    def add(self, block, pos=(0, 0, 0), rot=(0, 0, 0), scale=(1, 1, 1), mats=None, recolor=None,
            group="", name="", mirror=False) -> Part:
        """Place a block.

        mats    - list of material names, one per slot (see block_info(block)['slots'])
        recolor - dict {original slot material -> new material name}; unmapped slots keep defaults
        mirror  - also place a copy mirrored across X=0 (scale.x negated), returned part is the original
        """
        info = block_info(block)
        if isinstance(scale, (int, float)):
            scale = (scale, scale, scale)
        slots = list(info["slots"])
        if mats is not None:
            slots = list(mats) + slots[len(mats):]
        if recolor:
            slots = [recolor.get(s, s) for s in slots]
        p = Part(block, tuple(map(float, pos)), tuple(map(float, rot)), tuple(map(float, scale)),
                 slots, group, name)
        self.parts.append(p)
        if mirror:
            self.parts.append(Part(block, (-p.position[0], p.position[1], p.position[2]),
                                   (p.rotation[0], -p.rotation[1], -p.rotation[2]),
                                   (-p.scale[0], p.scale[1], p.scale[2]), list(slots), group,
                                   (name + "_mirror") if name else ""))
        return p

    def merge(self, other: "Model", offset=(0, 0, 0), group=None):
        for k, m in other.materials.items():
            self.materials.setdefault(k, m)
        for p in other.parts:
            q = Part(**{**p.__dict__})
            q.position = tuple(a + b for a, b in zip(p.position, offset))
            if group is not None:
                q.group = group
            self.parts.append(q)

    # ---- io
    def save(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        used = []
        for p in self.parts:
            for m in p.materials:
                if m not in used:
                    used.append(m)
        defaults = library()["materials"]
        lines = ["# Made using Asset Forge (2.5.3)", "", ":materials", ""]
        for m in used:
            mat = self.materials.get(m) or Material(m, (defaults.get(m) or [1, 1, 1, 1]))
            lines.append(mat.to_line())
        lines += ["", ":models", ""]
        lines += [p.to_line() for p in self.parts]
        path.write_text("\n".join(lines) + "\n")
        return path

    @classmethod
    def load(cls, path) -> "Model":
        m = cls()
        section = None
        for raw in Path(path).read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(":"):
                section = line[1:]
                continue
            d = {}
            for kv in line.strip("[]").split(";"):
                if ":" in kv:
                    k, v = kv.split(":", 1)
                    d[k] = v
            if section == "materials" and "name" in d:
                c = [float(x) for x in re.findall(r"-?[\d.]+", d["color"])]
                sc = tuple(float(x) for x in re.findall(r"-?[\d.]+", d.get("scale", "(1,1)")))
                m.materials[d["name"]] = Material(
                    d["name"], c, d.get("texture"), sc, d.get("shader", "Default"),
                    int(d.get("mapping", 0)), float(d.get("valueA", 0.25)), float(d.get("valueB", 0.25)))
            elif section == "models" and "type" in d:
                vec = lambda s: tuple(float(x) for x in re.findall(r"-?[\d.]+(?:[eE]-?\d+)?", s))
                m.parts.append(Part(
                    f"{d['collection']}/{d['type']}", vec(d["position"]), vec(d["rotation"]),
                    vec(d["scale"]), [x for x in d.get("materials", "").split("+") if x],
                    d.get("group", ""), d.get("name", ""), d.get("locked") == "True",
                    d.get("hidden") == "True"))
        return m

    # ---- outputs
    def assemble(self, **kw) -> "Mesh":
        return assemble(self, **kw)

    def export_glb(self, path, **kw):
        return export_glb(self, path, **kw)

    def render(self, path=None, **kw):
        return render(self.assemble(), path, **kw)

    def bounds(self):
        mesh = self.assemble()
        return mesh.pos.reshape(-1, 3).min(0), mesh.pos.reshape(-1, 3).max(0)


# ------------------------------------------------------------------ textures

def texture_ref(tex: str) -> str:
    """Normalise a texture spec to Asset Forge's '<folder>/<file>' reference."""
    p = Path(tex)
    if p.is_absolute() or str(tex).startswith(("Textures", "Asset Forge")):
        p = p.resolve()
        try:
            rel = p.relative_to(AF_TEXTURES.resolve())
            return rel.as_posix()
        except ValueError:
            pass
        return f"{p.parent.name}/{p.name}"
    return p.as_posix()


def load_texture(ref: str):
    """Return float RGB array for an AF texture reference, or None if not found."""
    if ref in _TEX_CACHE:
        return _TEX_CACHE[ref]
    cands = [AF_TEXTURES / ref, AF_TEXTURES / (ref + ".png"), ROOT / ref]
    folder, _, name = ref.partition("/")
    cands += list((AF_TEXTURES / folder).rglob(name)) if (AF_TEXTURES / folder).exists() else []
    img = None
    for c in cands:
        if c.exists() and c.is_file():
            img = np.asarray(Image.open(c).convert("RGB"), np.float32) / 255
            break
    _TEX_CACHE[ref] = img
    return img


# ------------------------------------------------------------------ assembly

def euler_matrix(deg):
    """Unity Quaternion.Euler: rotate Z, then X, then Y."""
    x, y, z = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Ry @ Rx @ Rz


@dataclass
class Mesh:
    """De-indexed triangle soup in glTF space (right-handed, +Y up, model front = -Z)."""
    pos: np.ndarray          # (T,3,3)
    nrm: np.ndarray          # (T,3,3) vertex normals
    uv: np.ndarray           # (T,3,2)
    mat: np.ndarray          # (T,) index into materials
    group: np.ndarray        # (T,) index into groups
    materials: list          # list[Material]
    groups: list             # list[str]


def _box_uv(world_tri):
    """Asset Forge UVMapping.BoxUV for de-indexed triangles in Unity world space."""
    a, b, c = world_tri[:, 0], world_tri[:, 1], world_tri[:, 2]
    n = np.cross(b - a, c - a)
    ax = np.abs(n)
    dirs = np.where((ax[:, 0] > ax[:, 1]) & (ax[:, 0] > ax[:, 2]), 1,
                    np.where(ax[:, 1] > ax[:, 2], 2, 3))
    sign = np.where(n[np.arange(len(n)), dirs - 1] < 0, -1.0, 1.0)
    uv = np.zeros(world_tri.shape[:2] + (2,), np.float32)
    for d in (1, 2, 3):
        m = dirs == d
        if not m.any():
            continue
        v, s = world_tri[m], sign[m][:, None]
        if d == 1:
            uv[m] = np.stack([v[..., 2] * s, v[..., 1]], -1)
        elif d == 2:
            uv[m] = np.stack([v[..., 0], v[..., 2] * s], -1)
        else:
            uv[m] = np.stack([v[..., 0] * -s, v[..., 1]], -1)
    return uv


def assemble(model: Model, include_hidden=False) -> Mesh:
    defaults = library()["materials"]
    mats: list[Material] = []
    mindex: dict[str, int] = {}
    groups: list[str] = []
    P, N, U, M, G = [], [], [], [], []

    def mat_id(name):
        if name not in mindex:
            m = model.materials.get(name)
            if m is None:
                c = defaults.get(name) or [0.8, 0.8, 0.8, 1]
                m = Material(name, list(c))
                tex = defaults.get(name + "#map")
                if tex:
                    m.texture = tex
                    m.mapping = 1
            mindex[name] = len(mats)
            mats.append(m)
        return mindex[name]

    for part in model.parts:
        if part.hidden and not include_hidden:
            continue
        pos, nrm, uvs, tris = load_mesh(part.block)
        R = euler_matrix(part.rotation)
        S = np.asarray(part.scale, np.float64)
        T = np.asarray(part.position, np.float64)
        wp = (pos * S) @ R.T + T
        nm = (nrm / np.where(S == 0, 1, S)) @ R.T if len(nrm) == len(pos) else np.zeros_like(wp)
        nm /= np.maximum(np.linalg.norm(nm, axis=1, keepdims=True), 1e-9)
        flip = np.prod(S) < 0
        gname = part.group or "body"
        if gname not in groups:
            groups.append(gname)
        gi = groups.index(gname)
        slot_names = part.materials or block_info(part.block)["slots"]
        for si, t in enumerate(tris):
            if len(t) == 0:
                continue
            t = t[:, ::-1] if flip else t
            name = slot_names[si] if si < len(slot_names) else slot_names[-1]
            mi = mat_id(name)
            tri_w = wp[t]
            m = mats[mi]
            if m.texture and m.mapping != 1:
                tuv = _box_uv(tri_w)
            else:
                tuv = uvs[t] if len(uvs) == len(pos) else np.zeros(t.shape + (2,), np.float32)
            tuv = tuv * np.asarray(m.scale[:2], np.float32)
            P.append(tri_w)
            N.append(nm[t])
            U.append(tuv)
            M.append(np.full(len(t), mi))
            G.append(np.full(len(t), gi))
    if not P:
        raise ValueError("model has no visible parts")
    pos = np.concatenate(P).astype(np.float32)
    nrm = np.concatenate(N).astype(np.float32)
    # Unity (left-handed) -> glTF (right-handed) the way Asset Forge/UniGLTF does: negate Z,
    # which mirrors handedness, so triangle winding is reversed too.
    pos[..., 2] *= -1
    nrm[..., 2] *= -1
    pos = pos[:, ::-1]
    nrm = nrm[:, ::-1]
    uv = np.concatenate(U).astype(np.float32)[:, ::-1]
    return Mesh(pos, nrm, uv, np.concatenate(M), np.concatenate(G), mats, groups)


# ------------------------------------------------------------------ GLB export

def export_glb(model: Model | Mesh, path, center="none", nodes="groups", scale=1.0, facing="-z"):
    """Write a binary glTF.

    center - 'none' (keep AF origin), 'base' (x/z centred, sits on y=0), 'bounds' (bbox centre)
    nodes  - 'groups' (one node per AF group, ungrouped -> 'body') or 'single'
    facing - '-z' (Asset Forge / Godot forward, default) or '+z' (glTF spec / three.js lookAt forward)
    """
    mesh = model if isinstance(model, Mesh) else assemble(model)
    pos = mesh.pos.copy() * scale
    nrm = mesh.nrm
    if facing == "+z":  # 180 degree turn about Y: keeps handedness, so winding is unchanged
        pos[..., [0, 2]] *= -1
        nrm = nrm.copy()
        nrm[..., [0, 2]] *= -1
    flat = pos.reshape(-1, 3)
    lo, hi = flat.min(0), flat.max(0)
    if center == "base":
        pos -= np.array([(lo[0] + hi[0]) / 2, lo[1], (lo[2] + hi[2]) / 2], np.float32)
    elif center == "bounds":
        pos -= ((lo + hi) / 2).astype(np.float32)

    bin_chunks: list[bytes] = []
    offset = 0
    gl = {"asset": {"version": "2.0", "generator": "Asset-Forge-Workspace forge.py"},
          "scene": 0, "scenes": [{"nodes": []}], "nodes": [], "meshes": [], "materials": [],
          "accessors": [], "bufferViews": [], "buffers": []}

    def add_view(arr: np.ndarray, target):
        nonlocal offset
        data = arr.tobytes()
        pad = (-len(data)) % 4
        gl["bufferViews"].append({"buffer": 0, "byteOffset": offset, "byteLength": len(data),
                                  **({"target": target} if target else {})})
        bin_chunks.append(data + b"\0" * pad)
        offset += len(data) + pad
        return len(gl["bufferViews"]) - 1

    def add_accessor(arr, ctype, typ, target, minmax=False):
        view = add_view(arr, target)
        acc = {"bufferView": view, "componentType": ctype, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            acc["min"] = arr.min(0).tolist()
            acc["max"] = arr.max(0).tolist()
        gl["accessors"].append(acc)
        return len(gl["accessors"]) - 1

    # materials + textures
    tex_index = {}
    for m in mesh.materials:
        lin = srgb_to_linear(m.color[:3]).tolist() + [float(m.color[3])]
        gm = {"name": m.name, "pbrMetallicRoughness": {
            "baseColorFactor": lin, "metallicFactor": float(min(m.value_a, 1.0)) if m.value_a < 0.5 else 0.5,
            "roughnessFactor": float(max(0.05, 1.0 - m.value_b))}}
        if m.shader == "Unlit":
            gm.setdefault("extensions", {})["KHR_materials_unlit"] = {}
            gl.setdefault("extensionsUsed", []).append("KHR_materials_unlit")
        if m.texture:
            img = load_texture(m.texture)
            if img is not None:
                if m.texture not in tex_index:
                    buf = io.BytesIO()
                    Image.fromarray((img * 255).astype(np.uint8)).save(buf, "PNG")
                    data = np.frombuffer(buf.getvalue(), np.uint8)
                    view = add_view(data, None)
                    gl.setdefault("images", []).append(
                        {"bufferView": view, "mimeType": "image/png", "name": Path(m.texture).stem})
                    gl.setdefault("samplers", [{"magFilter": 9728, "minFilter": 9984,
                                                "wrapS": 10497, "wrapT": 10497}])
                    gl.setdefault("textures", []).append({"source": len(gl["images"]) - 1, "sampler": 0})
                    tex_index[m.texture] = len(gl["textures"]) - 1
                gm["pbrMetallicRoughness"]["baseColorTexture"] = {"index": tex_index[m.texture]}
        gl["materials"].append(gm)

    group_ids = range(len(mesh.groups)) if nodes == "groups" else [None]
    for gi in group_ids:
        gmask = np.ones(len(pos), bool) if gi is None else mesh.group == gi
        if not gmask.any():
            continue
        prims = []
        for mi in np.unique(mesh.mat[gmask]):
            sel = gmask & (mesh.mat == mi)
            p = pos[sel].reshape(-1, 3)
            n = nrm[sel].reshape(-1, 3)
            uv = mesh.uv[sel].reshape(-1, 2)
            # weld identical vertices to keep files small
            key = np.concatenate([p, n, uv], 1)
            uniq, inv = np.unique(np.round(key, 5), axis=0, return_inverse=True)
            inv = inv.reshape(-1)
            p, n, uv = (uniq[:, :3].astype(np.float32), uniq[:, 3:6].astype(np.float32),
                        uniq[:, 6:8].astype(np.float32))
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
            idx = inv.astype(np.uint32 if len(p) > 65535 else np.uint16)
            attrs = {"POSITION": add_accessor(p, 5126, "VEC3", 34962, True),
                     "NORMAL": add_accessor(n, 5126, "VEC3", 34962)}
            if mesh.materials[mi].texture or mesh.materials[mi].mapping:
                uv = uv.copy()
                uv[:, 1] = 1.0 - uv[:, 1]  # Unity UV origin bottom-left -> glTF top-left
                attrs["TEXCOORD_0"] = add_accessor(uv, 5126, "VEC2", 34962)
            prims.append({"attributes": attrs, "material": int(mi),
                          "indices": add_accessor(idx, 5125 if idx.dtype == np.uint32 else 5123,
                                                  "SCALAR", 34963)})
        name = "model" if gi is None else mesh.groups[gi]
        gl["meshes"].append({"name": name, "primitives": prims})
        gl["nodes"].append({"name": name, "mesh": len(gl["meshes"]) - 1})
        gl["scenes"][0]["nodes"].append(len(gl["nodes"]) - 1)

    binary = b"".join(bin_chunks)
    gl["buffers"].append({"byteLength": len(binary)})
    js = json.dumps(gl, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    out = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binary))
    out += struct.pack("<II", len(js), 0x4E4F534A) + js
    out += struct.pack("<II", len(binary), 0x004E4942) + binary
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(out)
    return path


# ------------------------------------------------------------------ rendering

VIEWS = {
    # name: (direction from target to camera in glTF space, screen-up hint)
    "front": ((0, 0, -1), (0, 1, 0)),
    "back": ((0, 0, 1), (0, 1, 0)),
    "right": ((1, 0, 0), (0, 1, 0)),     # model's right side; front points to screen-right
    "left": ((-1, 0, 0), (0, 1, 0)),     # front points to screen-left
    "top": ((0, 1, 0), (0, 0, -1)),      # top-down; front points up the screen
    "bottom": ((0, -1, 0), (0, 0, 1)),
}


def view_dir(view: str):
    """Return (camera direction, up hint). Accepts presets or 'yaw,pitch' in degrees.

    'iso' = yaw 45 pitch 30 (front-right corner), 'iso_back', 'iso_left', 'dimetric' (pitch 26.565),
    'yaw,pitch' with yaw 0 = front, 90 = right side, pitch 90 = top.
    """
    presets = {"iso": (45, 30), "iso_left": (-45, 30), "iso_back": (135, 30),
               "iso_back_left": (-135, 30), "dimetric": (45, 26.565), "three_quarter": (35, 20),
               "high": (0, 50), "trueiso": (45, 35.264)}
    if view in VIEWS:
        d, up = VIEWS[view]
        return np.array(d, float), np.array(up, float)
    if view in presets:
        yaw, pitch = presets[view]
    else:
        yaw, pitch = (float(x) for x in view.split(","))
    y, p = math.radians(yaw), math.radians(pitch)
    d = np.array([math.sin(y) * math.cos(p), math.sin(p), -math.cos(y) * math.cos(p)])
    return d, np.array([0, 1, 0], float)


def _shade_colors(mesh: Mesh, light_vals, bary_uv, tri_idx):
    """Per-pixel base colour: material tint x (optional) texture sample."""
    out = np.empty((len(tri_idx), 3), np.float32)
    mats = mesh.mat[tri_idx]
    for mi in np.unique(mats):
        sel = mats == mi
        m = mesh.materials[mi]
        col = np.asarray(m.color[:3], np.float32)
        if m.texture:
            img = load_texture(m.texture)
            if img is not None:
                h, w = img.shape[:2]
                uv = bary_uv[sel]
                tx = np.floor((uv[:, 0] % 1.0) * w).astype(int) % w
                ty = np.floor((1 - uv[:, 1] % 1.0) * h).astype(int) % h
                out[sel] = img[ty, tx] * col
                continue
        out[sel] = col
    return out * light_vals[:, None]


def rasterize(mesh: Mesh, size=512, view="iso", margin=0.06, ppu=None, light=None,
              ambient=0.5, diffuse=0.6, bands=0):
    """Orthographic z-buffer render -> (H,W,4) float RGBA.

    ppu   - fixed pixels per unit (keeps a consistent scale across a sprite set)
    bands - quantise diffuse light into N cel-shading steps (0 = smooth)
    """
    W = H = size
    d, up = view_dir(view)
    d /= np.linalg.norm(d)
    f = -d
    r = np.cross(f, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, f)
    pts = mesh.pos.reshape(-1, 3)
    sx, sy, sz = pts @ r, pts @ u, pts @ d
    if ppu is None:
        span = max(sx.max() - sx.min(), sy.max() - sy.min(), 1e-6)
        ppu = size * (1 - 2 * margin) / span
    cx, cy = (sx.max() + sx.min()) / 2, (sy.max() + sy.min()) / 2
    X = ((sx - cx) * ppu + W / 2).reshape(-1, 3)
    Y = (H / 2 - (sy - cy) * ppu).reshape(-1, 3)
    Z = sz.reshape(-1, 3)

    # light fixed relative to camera: upper-left-front key light
    L = light if light is not None else (-0.45 * r + 0.75 * u + 0.5 * d)
    L = np.asarray(L, float) / np.linalg.norm(L)
    a, b, c = mesh.pos[:, 0], mesh.pos[:, 1], mesh.pos[:, 2]
    fn = np.cross(b - a, c - a)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    facing = np.sign(fn @ d)
    facing[facing == 0] = 1
    fn *= facing[:, None]  # two-sided lighting
    # back faces lose depth ties, so coincident double-sided shells show their camera-facing side (like culling)
    Z = Z - np.where(facing < 0, 1e-4 * max(float(np.ptp(sz)), 1e-6), 0.0)[:, None]
    k = np.clip(fn @ L, 0, None)
    if bands:
        k = np.round(k * bands) / bands
    lit = ambient + diffuse * k

    zbuf = np.full((H, W), -np.inf, np.float32)
    tbuf = np.full((H, W), -1, np.int64)
    ubuf = np.zeros((H, W, 2), np.float32)
    order = np.argsort(-Z.max(1))  # front to back for early rejects
    for t in order:
        x0, y0 = X[t], Y[t]
        xmin, xmax = max(int(np.floor(x0.min())), 0), min(int(np.ceil(x0.max())), W - 1)
        ymin, ymax = max(int(np.floor(y0.min())), 0), min(int(np.ceil(y0.max())), H - 1)
        if xmin > xmax or ymin > ymax:
            continue
        den = (y0[1] - y0[2]) * (x0[0] - x0[2]) + (x0[2] - x0[1]) * (y0[0] - y0[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
        w0 = ((y0[1] - y0[2]) * (gx - x0[2]) + (x0[2] - x0[1]) * (gy - y0[2])) / den
        w1 = ((y0[2] - y0[0]) * (gx - x0[2]) + (x0[0] - x0[2]) * (gy - y0[2])) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * Z[t, 0] + w1 * Z[t, 1] + w2 * Z[t, 2]
        sub = zbuf[ymin:ymax + 1, xmin:xmax + 1]
        win = inside & (z > sub)
        if not win.any():
            continue
        sub[win] = z[win]
        tbuf[ymin:ymax + 1, xmin:xmax + 1][win] = t
        uvt = mesh.uv[t]
        ubuf[ymin:ymax + 1, xmin:xmax + 1][win] = (w0[win, None] * uvt[0] + w1[win, None] * uvt[1]
                                                    + w2[win, None] * uvt[2])
    img = np.zeros((H, W, 4), np.float32)
    mask = tbuf >= 0
    if mask.any():
        tri = tbuf[mask]
        img[mask, :3] = _shade_colors(mesh, lit[tri], ubuf[mask], tri)
        img[mask, 3] = 1
    return np.clip(img, 0, 1)


def render(mesh: Mesh, path=None, size=512, view="iso", aa=2, bg=None, **kw):
    """High-quality preview: supersampled render, optional background colour."""
    img = rasterize(mesh, size * aa, view, **kw)
    if aa > 1:
        img = img.reshape(size, aa, size, aa, 4)
        a = img[..., 3].mean((1, 3))
        rgb = (img[..., :3] * img[..., 3:4]).sum((1, 3)) / np.maximum(img[..., 3].sum((1, 3)), 1e-6)[..., None]
        img = np.concatenate([rgb, a[..., None]], -1)
    out = Image.fromarray((img * 255).round().astype(np.uint8), "RGBA")
    if bg:
        base = Image.new("RGBA", out.size, tuple(int(v * 255) for v in hex_to_rgba(bg)))
        out = Image.alpha_composite(base, out)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        out.save(path)
    return out


def sprite(mesh: Mesh, path=None, size=64, view="right", colors=0, outline="dark", ppu=None,
           margin=0.04, upscale=1, bands=3, **kw):
    """Crisp pixel-art sprite: no AA, hard alpha, cel-banded light, optional 1px outline.

    bands   - light steps per material (3 = shadow/mid/light); keeps material colours pure
    colors  - optional extra median-cut palette limit (0 = off; useful with textures)
    outline - 'dark' (darkened neighbour colour), 'black', '#RRGGBB' or None
    upscale - integer nearest-neighbour upscale of the saved PNG (for previewing)
    """
    img = rasterize(mesh, size, view, margin=margin, ppu=ppu, bands=bands, **kw)
    rgb = (img[..., :3] * 255).round().astype(np.uint8)
    alpha = img[..., 3] > 0.5
    if colors:
        pal_img = Image.fromarray(rgb[alpha][None, :, :] if alpha.any() else rgb[:1])
        q = pal_img.quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        palette = np.asarray(q.getpalette()[:colors * 3], np.uint8).reshape(-1, 3)
        idx = np.asarray(q)[0]
        rgb[alpha] = palette[idx]
    out = np.zeros((size, size, 4), np.uint8)
    out[..., :3] = rgb
    out[..., 3] = alpha * 255
    if outline:
        a = alpha
        nb = np.zeros_like(a)
        nb[1:] |= a[:-1]
        nb[:-1] |= a[1:]
        nb[:, 1:] |= a[:, :-1]
        nb[:, :-1] |= a[:, 1:]
        edge = nb & ~a
        if outline == "black":
            col = np.array([12, 10, 16], np.uint8)
            out[edge, :3] = col
        elif outline.startswith("#"):
            out[edge, :3] = (np.asarray(hex_to_rgba(outline)[:3]) * 255).astype(np.uint8)
        else:  # darkened colour of an adjacent opaque pixel
            src = np.zeros((size, size, 3), np.float32)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                sh = np.roll(np.roll(out[..., :3].astype(np.float32) * a[..., None], dy, 0), dx, 1)
                src = np.maximum(src, sh)
            out[edge, :3] = (src[edge] * 0.28).astype(np.uint8)
        out[edge, 3] = 255
    im = Image.fromarray(out, "RGBA")
    if upscale > 1:
        im = im.resize((size * upscale, size * upscale), Image.NEAREST)
    if path:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        im.save(path)
    return im


def turnaround(mesh: Mesh, path, size=256, views=("front", "iso", "right", "iso_back", "back", "top"),
               bg="#2B2D33", label=None):
    """Grid sheet of several views for review."""
    tiles = [render(mesh, None, size, v, bg=bg) for v in views]
    cols = 3
    rows = math.ceil(len(tiles) / cols)
    sheet = Image.new("RGBA", (cols * size, rows * size), (20, 20, 24, 255))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % cols) * size, (i // cols) * size))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return sheet


def review_grid(items, path, size=160, cols=5, view="iso", bg="#2B2D33"):
    """Labelled thumbnail grid for batch review: items = [(label, Model | Mesh), ...] (25 = 5x5 per sheet)."""
    from PIL import ImageDraw
    rows = math.ceil(len(items) / cols)
    sheet = Image.new("RGBA", (cols * size, rows * (size + 14)), (20, 20, 24, 255))
    d = ImageDraw.Draw(sheet)
    for i, (label, m) in enumerate(items):
        mesh = m.assemble() if isinstance(m, Model) else m
        x, y = (i % cols) * size, (i // cols) * (size + 14)
        sheet.paste(render(mesh, None, size, view, bg=bg), (x, y))
        d.text((x + 3, y + size), str(label)[:26], fill=(220, 220, 225))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return sheet


def rotate_y(mesh: Mesh, deg: float) -> Mesh:
    """Copy of the mesh turned like an Asset Forge rotation of `deg` about +Y (for sprite rotation sets)."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]], np.float32)  # Unity Ry(deg) expressed in glTF space
    return Mesh(mesh.pos @ R.T, mesh.nrm @ R.T, mesh.uv, mesh.mat, mesh.group, mesh.materials, mesh.groups)


def fit_ppu(meshes, size, view="right", margin=0.04, rotations=1) -> float:
    """Largest pixels-per-unit at which every mesh (and each of its rotations) fits the canvas.

    Pass the result as `ppu` to every sprite of a set so they share one scale."""
    best = float("inf")
    d, up = view_dir(view)
    d /= np.linalg.norm(d)
    r = np.cross(-d, up)
    r /= np.linalg.norm(r)
    u = np.cross(r, -d)
    for mesh in meshes:
        for k in range(rotations):
            pts = rotate_y(mesh, k * 360 / rotations).pos.reshape(-1, 3)
            sx, sy = pts @ r, pts @ u
            span = max(sx.max() - sx.min(), sy.max() - sy.min(), 1e-6)
            best = min(best, size * (1 - 2 * margin) / span)
    return best


# ------------------------------------------------------------------ delivery

def deliver(model: Model, name: str, wip_dir, out_dir=None, center="base", sprites=(), sheet=True,
            preview_view="iso", facing="-z"):
    """Standard outputs for one asset.

    wip_dir  - Workbench folder: <name>.model (opens in Asset Forge), preview + review sheet
    out_dir  - Assets folder for the finished deliverable: <name>.glb (+ sprites); None = wip_dir
    sprites  - iterable of dicts for sprite(): e.g. {"view": "right", "size": 64}; add "rotations": 8 for a
               rotation set (<name>_sprite_<view>_<size>_r000.png, _r045 ... turned about +Y)
    """
    wip_dir = Path(wip_dir)
    out_dir = Path(out_dir) if out_dir else wip_dir
    wip_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save(wip_dir / f"{name}.model")
    mesh = model.assemble()
    export_glb(mesh, out_dir / f"{name}.glb", center=center, facing=facing)
    render(mesh, out_dir / f"{name}_preview.png", 512, preview_view, bg="#2B2D33")
    if sheet:
        turnaround(mesh, wip_dir / f"{name}_sheet.png")
    for s in sprites:
        s = dict(s)
        tag = f"{s.get('view', 'right')}_{s.get('size', 64)}"
        up = s.pop("upscale_preview", 0)
        n = int(s.pop("rotations", 1))
        for k in range(n):
            deg = k * 360 / n
            rm, rtag = (rotate_y(mesh, deg), f"{tag}_r{round(deg):03d}") if n > 1 else (mesh, tag)
            sprite(rm, out_dir / f"{name}_sprite_{rtag}.png", **s)
            if up:
                sprite(rm, wip_dir / f"{name}_sprite_{rtag}_x{up}.png", upscale=up, **s)
    flat = mesh.pos.reshape(-1, 3)
    size = flat.max(0) - flat.min(0)
    print(f"{name}: {len(mesh.pos)} tris, size {size.round(2).tolist()} -> {out_dir}")
    return mesh


# ------------------------------------------------------------------ CLI

def _cli():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("export", help=".model -> .glb")
    s.add_argument("model")
    s.add_argument("out", nargs="?")
    s.add_argument("--center", default="none", choices=["none", "base", "bounds"])
    s.add_argument("--nodes", default="groups", choices=["groups", "single"])
    s.add_argument("--scale", type=float, default=1.0)
    s.add_argument("--facing", default="-z", choices=["-z", "+z"])

    s = sub.add_parser("render", help=".model -> preview PNG")
    s.add_argument("model")
    s.add_argument("out")
    s.add_argument("--view", default="iso")
    s.add_argument("--size", type=int, default=512)
    s.add_argument("--bg")

    s = sub.add_parser("sheet", help=".model -> multi-view review sheet")
    s.add_argument("model")
    s.add_argument("out")
    s.add_argument("--size", type=int, default=256)

    s = sub.add_parser("sprite", help=".model -> pixel-art sprite")
    s.add_argument("model")
    s.add_argument("out")
    s.add_argument("--view", default="right")
    s.add_argument("--size", type=int, default=64)
    s.add_argument("--colors", type=int, default=0)
    s.add_argument("--bands", type=int, default=3)
    s.add_argument("--outline", default="dark")
    s.add_argument("--ppu", type=float)
    s.add_argument("--upscale", type=int, default=1)

    s = sub.add_parser("find", help="search blocks by regex")
    s.add_argument("pattern")
    s.add_argument("--collection")
    s.add_argument("--deluxe", action="store_true")

    s = sub.add_parser("info", help="block metadata")
    s.add_argument("block")

    a = ap.parse_args()
    if a.cmd == "find":
        for k in find(a.pattern, a.collection, a.deluxe):
            b = library()["blocks"][k]
            size = [round(h - l, 2) for l, h in zip(b["min"], b["max"])]
            lo = [round(v, 2) for v in b["min"]]
            hi = [round(v, 2) for v in b["max"]]
            print(f"{k:50s} size={size} min={lo} max={hi} slots={b['slots']}")
        return
    if a.cmd == "info":
        print(json.dumps(block_info(a.block), indent=1))
        return
    m = Model.load(a.model)
    if a.cmd == "export":
        out = a.out or str(Path(a.model).with_suffix(".glb"))
        print(export_glb(m, out, a.center, a.nodes, a.scale, a.facing))
    elif a.cmd == "render":
        render(m.assemble(), a.out, a.size, a.view, bg=a.bg)
    elif a.cmd == "sheet":
        turnaround(m.assemble(), a.out, a.size)
    elif a.cmd == "sprite":
        outline = None if a.outline in ("none", "") else a.outline
        sprite(m.assemble(), a.out, a.size, a.view, a.colors, outline, a.ppu, upscale=a.upscale,
               bands=a.bands)


if __name__ == "__main__":
    _cli()
