"""Turn custom-collection OBJs 180 degrees about Y, in place, so they face +z like Asset Forge's blocks.

  .venv/Scripts/python forge/rotate_collection.py <Collection> [--only "stem" "stem" ...] [--dry-run]

Only `v` and `vn` lines change (x and z negated; the sign is toggled on the original text, so no
precision is lost). Everything else, including line endings, stays byte-identical. Before writing,
the whole collection folder is copied to C:/trash/collections-original/<Collection> unless a backup
already exists there. Afterwards run extract_library.py --custom-only and catalogue.py.
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = ROOT / "Asset Forge 2.5.3 (Windows)" / "Collections"
BACKUP = Path("C:/trash/collections-original")
VLINE = re.compile(rb"^(\s*vn?\s+)(\S+)(\s+)(\S+)(\s+)(\S+)(.*)$", re.S)


def neg(tok: bytes) -> bytes:
    if tok.startswith(b"-"):
        return tok[1:]
    return b"-" + (tok[1:] if tok.startswith(b"+") else tok)


def rotate_obj(path: Path) -> int:
    out, n = [], 0
    for line in path.read_bytes().splitlines(keepends=True):
        body = line.rstrip(b"\r\n")
        end = line[len(body):]
        m = VLINE.match(body)  # `v`/`vn` only: vt, f, usemtl ... never match
        if m:
            g = list(m.groups())
            g[1], g[5] = neg(g[1]), neg(g[5])
            body = b"".join(g)
            n += 1
        out.append(body + end)
    path.write_bytes(b"".join(out))
    return n


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    name = args[0]
    only = args[args.index("--only") + 1:] if "--only" in args else None
    if only:
        only = [s for s in only if not s.startswith("--")]
    folder = COLLECTIONS / name
    objs = sorted(folder.glob("*.obj"))
    if only:
        missing = set(only) - {p.stem for p in objs}
        if missing:
            sys.exit(f"not found in {name}: {sorted(missing)}")
        objs = [p for p in objs if p.stem in only]
    if "--dry-run" in args:
        print("\n".join(p.name for p in objs))
        return
    if not (BACKUP / name).exists():
        shutil.copytree(folder, BACKUP / name)
        print(f"backed up {folder} -> {BACKUP / name}")
    total = 0
    for p in objs:
        total += rotate_obj(p)
    print(f"{name}: rotated {len(objs)} OBJs ({total} v/vn lines)")


if __name__ == "__main__":
    main()
