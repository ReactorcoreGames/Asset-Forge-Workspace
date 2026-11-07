"""Normalise a third-party OBJ pack into a standard Asset Forge collection (copies; the source is never touched).

  .venv/Scripts/python forge/import_collection.py <source_dir> --config forge/packs/<pack>.json [--dry-run] [--force]

Writes Asset Forge 2.5.3 (Windows)/Collections/<collection>/ : one OBJ per source model, a shared
<collection>.mtl with the config's neutral slots, and README.md (credit + what was done). Scale, pivot,
facing and slots are baked into v/vn, so no meta.ini is needed. All placement maths happens in Asset
Forge (Unity) space, i.e. after the loader's x negation, and is mapped back to OBJ space on write.

Config keys (see forge/packs/rc_primitives.json):
  collection, credit, scale, strip_prefix, pad (zero-pad numbers in names), rename {stem: name}
  slots {name: "#hex"}: the first slot is the default for every face
  slot_rules [{match, slot, faces: all|inward|back|flat_at, axis, level}]: applied in order, later wins
  pieces [{match, src_offset, yaw, align {x|y|z: axis|min|max|centre}}]: regex on the source stem;
      default align is x/z = axis (keep the source origin), y = min (bottom on y=0)
Zero-area triangles are dropped. --force moves an existing collection folder to C:/trash first.
"""
import json
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = ROOT / "Asset Forge 2.5.3 (Windows)" / "Collections"
TRASH = Path("C:/trash")


def read_obj(path):
    v, vt, vn, faces = [], [], [], []
    for line in path.read_text(errors="ignore").splitlines():
        p = line.split()
        if not p:
            continue
        if p[0] == "v":
            v.append([float(x) for x in p[1:4]])
        elif p[0] == "vt":
            vt.append([float(x) for x in p[1:3]])
        elif p[0] == "vn":
            vn.append([float(x) for x in p[1:4]])
        elif p[0] == "f":
            idx = []
            for c in p[1:]:
                parts = (c.split("/") + ["", ""])[:3]
                idx.append(tuple(int(x) - 1 if x else -1 for x in parts))
            for i in range(1, len(idx) - 1):  # fan, like Asset Forge's loader
                faces.append((idx[0], idx[i], idx[i + 1]))
    return np.array(v, float), np.array(vt, float).reshape(-1, 2), np.array(vn, float).reshape(-1, 3), faces


def key_of(stem, cfg):
    """Source stem minus strip_prefix: what rename, pieces and slot_rules match against."""
    pre = cfg.get("strip_prefix", "")
    return stem[len(pre):] if pre and stem.startswith(pre) else stem


def clean_name(stem, cfg):
    s = key_of(stem, cfg)
    if s in cfg.get("rename", {}):
        return cfg["rename"][s]
    pad = cfg.get("pad", 0)
    words = []
    for part in s.split("_"):
        for tok in re.findall(r"\d+x\d+|\d+[a-z]*|[A-Z]+(?![a-z])|[A-Z]?[a-z]+", part):
            tok = re.sub(r"\d+", lambda m: m.group().zfill(pad), tok)
            words.append(tok.lower())
    return "_".join(words)


def settings(stem, cfg):
    s = {"src_offset": [0, 0, 0], "yaw": 0, "align": {"x": "axis", "y": "min", "z": "axis"}}
    for p in cfg.get("pieces", []):
        if re.search(p["match"], stem):
            s["src_offset"] = p.get("src_offset", s["src_offset"])
            s["yaw"] = p.get("yaw", s["yaw"])
            s["align"] = {**s["align"], **p.get("align", {})}
    return s


def assign_slots(stem, V, faces, cfg):
    """Slot index per face, decided in source space (origin = the author's origin)."""
    names = list(cfg["slots"])
    slot = np.zeros(len(faces), int)
    tri = V[np.array([[f[0][0], f[1][0], f[2][0]] for f in faces])]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    cen = tri.mean(1)
    for r in cfg.get("slot_rules", []):
        if not re.search(r["match"], stem):
            continue
        kind = r["faces"]
        if kind == "all":
            sel = np.ones(len(faces), bool)
        elif kind == "inward":
            sel = (n * cen).sum(1) < 0
        elif kind == "back":
            ax = r.get("axis", "auto")
            ax = int(np.abs(n).mean(0).argmax()) if ax == "auto" else "xyz".index(ax)
            sel = n[:, ax] < 0
        elif kind == "flat_at":
            lvl = V[:, 1].min() if r.get("level", "min") == "min" else V[:, 1].max()
            sel = (n[:, 1] > 0.999) & (np.abs(tri[:, :, 1] - lvl).max(1) < 1e-4)
        else:
            raise ValueError(f"unknown slot rule faces={kind}")
        slot[sel] = names.index(r["slot"])
    return slot


def transform(V, N, s, scale):
    """Source OBJ space -> standardised Asset Forge space -> back to OBJ space."""
    P = (V + np.asarray(s["src_offset"], float)) * scale
    P[:, 0] *= -1
    N = N.copy()
    N[:, 0] *= -1
    a = np.radians(s["yaw"])
    c, sn = np.cos(a), np.sin(a)
    R = np.array([[c, 0, sn], [0, 1, 0], [-sn, 0, c]])  # Unity rotation about +Y
    P, N = P @ R.T, N @ R.T
    lo, hi = P.min(0), P.max(0)
    for i, ax in enumerate("xyz"):
        mode = s["align"][ax]
        P[:, i] -= {"axis": 0.0, "min": lo[i], "max": hi[i], "centre": (lo[i] + hi[i]) / 2}[mode]
    af_min, af_max = P.min(0), P.max(0)
    P[:, 0] *= -1
    N[:, 0] *= -1
    return P, N, af_min, af_max


def fmt(x):
    t = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def write_obj(path, name, mtl, P, VT, N, faces, slot, slot_names):
    out = [f"# {name}: standardised by forge/import_collection.py", f"mtllib {mtl}", f"o {name}"]
    out += [f"v {fmt(a)} {fmt(b)} {fmt(c)}" for a, b, c in P]
    out += [f"vt {fmt(a)} {fmt(b)}" for a, b in VT]
    out += [f"vn {fmt(a)} {fmt(b)} {fmt(c)}" for a, b, c in N]
    for si, sname in enumerate(slot_names):
        fs = [f for f, s in zip(faces, slot) if s == si]
        if not fs:
            continue
        out += [f"usemtl {sname}", "s off"]
        for f in fs:
            out.append("f " + " ".join("/".join("" if i < 0 else str(i + 1) for i in c) for c in f))
    path.write_text("\n".join(out) + "\n")


def main():
    args = sys.argv[1:]
    if not args or "--config" not in args:
        sys.exit(__doc__)
    src = Path(args[0])
    cfg = json.loads(Path(args[args.index("--config") + 1]).read_text())
    name = cfg["collection"]
    dest = COLLECTIONS / name
    dry = "--dry-run" in args
    objs = sorted(src.glob("*.obj"))
    if not objs:
        sys.exit(f"no OBJs in {src}")
    if dest.exists() and not dry:
        if "--force" not in args:
            sys.exit(f"{dest} exists (use --force to move it to {TRASH} and rebuild)")
        TRASH.mkdir(exist_ok=True)
        shutil.move(str(dest), str(TRASH / f"{name}_{time.strftime('%Y%m%d-%H%M%S')}"))
    names = [clean_name(p.stem, cfg) for p in objs]
    dupes = {n for n in names if names.count(n) > 1}
    if dupes:
        sys.exit(f"name clash after renaming: {sorted(dupes)}")
    if not dry:
        dest.mkdir(parents=True)
    slot_names = list(cfg["slots"])
    mtl = f"{name}.mtl"
    rows, total, dropped = [], 0, 0
    for obj, new in zip(objs, names):
        V, VT, N, faces = read_obj(obj)
        tri = V[np.array([[f[0][0], f[1][0], f[2][0]] for f in faces])]
        area = np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
        keep = area > 1e-9
        dropped += int((~keep).sum())
        faces = [f for f, k in zip(faces, keep) if k]
        slot = assign_slots(key_of(obj.stem, cfg), V, faces, cfg)
        s = settings(key_of(obj.stem, cfg), cfg)
        P, NN, lo, hi = transform(V, N, s, cfg["scale"])
        if not dry:
            write_obj(dest / f"{new}.obj", new, mtl, P, VT, NN, faces, slot, slot_names)
        used = [slot_names[i] for i in sorted(set(slot))]
        total += len(faces)
        rows.append((obj.stem, new, len(faces), (~keep).sum(), lo, hi, s["yaw"], used))
        print(f"{obj.stem:32s} -> {new:34s} tris {len(faces):5d} yaw {s['yaw']:4d} "
              f"min {np.round(lo, 3)} max {np.round(hi, 3)} slots {used}")
    print(f"{len(objs)} models, {total} tris, {dropped} zero-area tris dropped" + (" (dry run)" if dry else f" -> {dest}"))
    if dry:
        return
    lines = [f"# {name} materials (neutral defaults, recolour per model)"]
    for sname, hexc in cfg["slots"].items():
        r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
        lines += ["", f"newmtl {sname}", "Ns 0", "Ka 0 0 0", f"Kd {r:.4f} {g:.4f} {b:.4f}", "Ks 0 0 0", "d 1", "illum 1"]
    (dest / mtl).write_text("\n".join(lines) + "\n")
    readme = [f"# {name}", "", cfg.get("credit", ""), "",
              f"Generated from `{src.name}` by `forge/import_collection.py` with `{args[args.index('--config') + 1]}`. "
              f"Scale x{cfg['scale']}, pivots bottom-centre unless noted, front = +z, slots: "
              + ", ".join(f"`{k}` {v}" for k, v in cfg["slots"].items()) + ". Rebuild rather than edit by hand.", "",
              "| source | block | tris | yaw | slots |", "|---|---|---|---|---|"]
    readme += [f"| {r[0]} | {r[1]} | {r[2]} | {r[6]} | {', '.join(r[7])} |" for r in rows]
    (dest / "README.md").write_text("\n".join(readme) + "\n")


if __name__ == "__main__":
    main()
