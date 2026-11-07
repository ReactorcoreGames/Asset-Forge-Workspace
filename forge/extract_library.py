"""Extract every Asset Forge block (built-in + custom collections) into Library/.

Built-in blocks live as prefabs inside Asset Forge's Unity data files; custom
collections are plain OBJ folders. Both are normalised into one cache:

  Library/blocks/<Collection>/<type>.npz   positions, normals, uvs, tris_0..n
  Library/library.json                     per-block metadata (slots, bounds)

Mesh data is stored in Asset Forge's own (Unity, left-handed) space so the
transforms written in .model files apply to it unchanged.

Run once after installing/adding collections:  .venv/Scripts/python forge/extract_library.py
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
AF = ROOT / "Asset Forge 2.5.3 (Windows)"
LIB = ROOT / "Library"
EDITOR_PREFABS = {"SceneGizmo", "gizmo", "gizmoRotation", "studio"}


def color_to_list(c):
    return [round(float(c.r), 4), round(float(c.g), 4), round(float(c.b), 4), round(float(c.a), 4)]


def extract_builtin(meta, materials):
    import UnityPy
    from UnityPy.helpers.MeshHelper import MeshHandler

    env = UnityPy.load(str(AF / "Asset Forge_Data"))
    roots = {}
    for o in env.objects:
        if o.type.name != "Transform":
            continue
        try:
            t = o.read()
        except Exception:
            continue
        if t.m_Father.path_id != 0 or len(t.m_Children) == 0:
            continue
        roots.setdefault(t.m_GameObject.read().m_Name, []).append(t)

    for cname, transforms in sorted(roots.items()):
        # Duplicated prefabs (Collections + Collections Process) are identical; keep the largest.
        t = max(transforms, key=lambda x: len(x.m_Children))
        blocks = []
        for child_ptr in t.m_Children:
            child = child_ptr.read()
            go = child.m_GameObject.read()
            mf = mr = None
            for comp in go.m_Component:
                ptr = comp.component if hasattr(comp, "component") else comp[1]
                tn = ptr.type.name if hasattr(ptr, "type") else None
                try:
                    if tn == "MeshFilter":
                        mf = ptr.read()
                    elif tn == "MeshRenderer":
                        mr = ptr.read()
                except Exception:
                    pass
            if mf is None or mr is None or mf.m_Mesh.path_id == 0:
                continue
            blocks.append((go.m_Name, mf.m_Mesh.read(), mr))
        if len(blocks) < 3 or cname in EDITOR_PREFABS:
            continue  # UI prefabs, gizmos, cameras etc.

        out = LIB / "blocks" / cname
        out.mkdir(parents=True, exist_ok=True)
        for name, mesh, mr in blocks:
            h = MeshHandler(mesh)
            h.process()
            pos = np.asarray(h.m_Vertices, np.float32).reshape(-1, 3)
            nrm = np.asarray(h.m_Normals or [], np.float32).reshape(-1, 3)
            uv = np.asarray(h.m_UV0 or [], np.float32).reshape(-1, 2)
            tris = h.get_triangles()
            slots = []
            for mp in mr.m_Materials:
                if mp.path_id == 0:
                    slots.append("")
                    continue
                m = mp.read()
                slots.append(m.m_Name)
                if m.m_Name not in materials:
                    col = None
                    for k, v in m.m_SavedProperties.m_Colors:
                        if k == "_Color":
                            col = color_to_list(v)
                    materials[m.m_Name] = col
            save_block(out / f"{safe(name)}.npz", pos, nrm, uv, tris)
            meta.append(block_meta(cname, name, "builtin", pos, tris, slots))
        print(f"{cname}: {len(blocks)} blocks")


def safe(name):
    return name.replace("%", "_pct_")


def save_block(path, pos, nrm, uv, tris):
    arrays = {"positions": pos, "normals": nrm, "uvs": uv}
    for i, t in enumerate(tris):
        arrays[f"tris_{i}"] = np.asarray(t, np.int32).reshape(-1, 3)
    np.savez_compressed(path, **arrays)


def block_meta(cname, name, kind, pos, tris, slots):
    lo, hi = (pos.min(0), pos.max(0)) if len(pos) else (np.zeros(3), np.zeros(3))
    return {
        "collection": cname,
        "type": name,
        "kind": kind,
        "deluxe": "%" in name,
        "slots": slots,
        "min": [round(float(x), 4) for x in lo],
        "max": [round(float(x), 4) for x in hi],
        "tris": int(sum(len(t) for t in tris) // (1 if tris and np.ndim(tris[0]) == 2 else 3)),
    }


# ---------------------------------------------------------------- custom (OBJ)

def parse_mtl(path):
    mats, cur = {}, None
    if not path.exists():
        return mats
    for line in path.read_text(errors="ignore").splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "newmtl":
            cur = " ".join(p[1:])
            mats[cur] = {"Kd": [0.8, 0.8, 0.8], "map": None}
        elif cur and p[0] == "Kd":
            mats[cur]["Kd"] = [float(x) for x in p[1:4]]
        elif cur and p[0] == "map_Kd":
            mats[cur]["map"] = " ".join(p[1:])
    return mats


def load_obj(path):
    """OBJ -> Unity space the way Asset Forge's OBJLoader (Dummiesman) does it: x is negated."""
    v, vn, vt = [], [], []
    groups = {}  # material -> list of (vi, ti, ni) triples per triangle
    mtl_files, cur = [], ""
    for line in path.read_text(errors="ignore").splitlines():
        if not line or line[0] == "#":
            continue
        p = line.split()
        if not p:
            continue
        k = p[0]
        if k == "v":
            v.append([float(x) for x in p[1:4]])
        elif k == "vn":
            vn.append([float(x) for x in p[1:4]])
        elif k == "vt":
            vt.append([float(x) for x in p[1:3]])
        elif k == "usemtl":
            cur = " ".join(p[1:])
        elif k == "mtllib":
            mtl_files.append(" ".join(p[1:]))
        elif k == "f":
            idx = []
            for c in p[1:]:
                parts = c.split("/")
                vi = int(parts[0])
                ti = int(parts[1]) if len(parts) > 1 and parts[1] else 0
                ni = int(parts[2]) if len(parts) > 2 and parts[2] else 0
                idx.append((vi, ti, ni))
            g = groups.setdefault(cur, [])
            for i in range(1, len(idx) - 1):
                g.append((idx[0], idx[i], idx[i + 1]))
    V = np.asarray(v, np.float32)
    N = np.asarray(vn, np.float32) if vn else None
    T = np.asarray(vt, np.float32) if vt else None

    def res(i, n):
        return i - 1 if i > 0 else n + i

    pos, nrm, uv, tris, slots, remap = [], [], [], [], [], {}
    for mat, faces in groups.items():
        sub = []
        for face in faces:
            tri = []
            for vi, ti, ni in face:
                key = (vi, ti, ni)
                if key not in remap:
                    remap[key] = len(pos)
                    pos.append(V[res(vi, len(V))])
                    nrm.append(N[res(ni, len(N))] if (N is not None and ni) else [0, 0, 0])
                    uv.append(T[res(ti, len(T))] if (T is not None and ti) else [0, 0])
                tri.append(remap[key])
            # x flip mirrors the mesh, so reverse winding to keep faces outward
            sub.append([tri[0], tri[2], tri[1]])
        tris.append(np.asarray(sub, np.int32))
        slots.append(mat)
    pos = np.asarray(pos, np.float32).reshape(-1, 3)
    nrm = np.asarray(nrm, np.float32).reshape(-1, 3)
    pos[:, 0] *= -1
    nrm[:, 0] *= -1
    return pos, nrm, np.asarray(uv, np.float32).reshape(-1, 2), tris, slots, mtl_files


def extract_custom(meta, materials):
    cdir = AF / "Collections"
    for d in sorted(p for p in cdir.iterdir() if p.is_dir()):
        objs = sorted(d.glob("*.obj"))
        if not objs:
            continue
        scale, rot = 1.0, [0.0, 0.0, 0.0]
        ini = d / "meta.ini"
        if ini.exists():
            for line in ini.read_text().splitlines():
                if "scale" in line:
                    scale = float(line.split("=")[1])
                if "rotation" in line:
                    rot = [float(x) for x in re.findall(r"-?[\d.]+", line.split("=")[1])]
        out = LIB / "blocks" / d.name
        out.mkdir(parents=True, exist_ok=True)
        prefix = d.name.lower().replace(" ", "_")
        for obj in objs:
            pos, nrm, uv, tris, slots, mtls = load_obj(obj)
            mats = {}
            for m in mtls:
                mats.update(parse_mtl(d / m))
            # Asset Forge names custom materials "<collection>-<material>"
            full_slots = [f"{prefix}-{s}" for s in slots]
            for s, fs in zip(slots, full_slots):
                if fs not in materials:
                    info = mats.get(s, {"Kd": [0.8, 0.8, 0.8], "map": None})
                    materials[fs] = info["Kd"] + [1.0]
                    if info["map"]:
                        materials[fs + "#map"] = str((d / info["map"]).relative_to(ROOT))
            save_block(out / f"{safe(obj.stem)}.npz", pos, nrm, uv, tris)
            m = block_meta(d.name, obj.stem, "custom", pos, tris, full_slots)
            m["import_scale"] = scale
            m["import_rotation"] = rot
            meta.append(m)
        print(f"{d.name} (custom): {len(objs)} blocks, scale={scale}")


def main():
    LIB.mkdir(exist_ok=True)
    meta, materials = [], {}
    if "--custom-only" not in sys.argv:
        extract_builtin(meta, materials)
    else:
        old = json.loads((LIB / "library.json").read_text())
        meta = [b for b in old["blocks"] if b["kind"] == "builtin"]
        materials = old["materials"]
    extract_custom(meta, materials)
    for b in meta:
        b["tris"] = int(sum(np.load(LIB / "blocks" / b["collection"] / f"{safe(b['type'])}.npz")[k].shape[0]
                            for k in np.load(LIB / "blocks" / b["collection"] / f"{safe(b['type'])}.npz").files
                            if k.startswith("tris_")))
    (LIB / "library.json").write_text(json.dumps({"blocks": meta, "materials": materials}, indent=1))
    print(f"total {len(meta)} blocks, {len(materials)} materials")


if __name__ == "__main__":
    main()
