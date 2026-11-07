"""Parse a work order (WorkOrders/<project>.md or any .md/.txt list) into one plan.

Format (written by WorkOrders/order-form.html, documented in WorkOrders/TEMPLATE.md):

  ```order                       header: one `key: value` per line (```yaml also accepted)
  project: desert-convoy
  surface: m32
  ...
  ```
  | # | name | description | qty | ref | notes |     items as table rows ...
  - item: scout_buggy                                 ... and/or as snippet blocks
    desc: two-seat buggy
    qty: 6

Per-item overrides go in notes as `key=value` (separated by `;`), e.g. `surface=flat; sprite_size=32`.

  .venv/Scripts/python forge/workorder.py WorkOrders/desert-convoy.md          # summary + checks
  .venv/Scripts/python forge/workorder.py WorkOrders/desert-convoy.md --json   # full plan as JSON

From Python: `from workorder import load_order, sprite_specs`.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DEFAULTS = {
    "project": "untitled", "route": "B", "engine": "godot", "facing": "-z", "surface": "flat",
    "texture": "none", "palette": "free choice", "glb": "yes", "sprites": "no", "sprite_views": "right",
    "sprite_size": "64", "sprite_outline": "dark", "sprite_same_scale": "yes", "sprite_rotations": "1",
    "detail": "broad", "notes": "",
}
ITEM_KEYS = {"item": "name", "name": "name", "desc": "desc", "description": "desc", "qty": "qty",
             "ref": "ref", "notes": "notes"}
BIG_ORDER = 25


def _kv(line):
    k, _, v = line.partition(":")
    v = re.sub(r"(^|\s+)#\s.*$", "", v)  # "# comment" (a hash then a space); hex codes like #C2A878 survive
    return k.strip().lower(), v.strip()


def parse(text: str) -> dict:
    header, items, warnings = {}, [], []
    lines = text.splitlines()
    i = 0
    cols = None
    cur = None
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if re.match(r"^```\s*(order|yaml)\s*$", s, re.I):
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                if ":" in lines[i] and not lines[i].strip().startswith("#"):
                    k, v = _kv(lines[i])
                    header[k] = v
                i += 1
            i += 1
            continue
        # table rows: a header row naming the columns, then data rows
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            low = [c.lower() for c in cells]
            if "name" in low and ("description" in low or "desc" in low):
                cols = [ITEM_KEYS.get(c, c) for c in low]
            elif cols and not all(re.fullmatch(r":?-+:?", c) for c in cells if c):
                row = dict(zip(cols, cells))
                if row.get("name") or row.get("desc") or row.get("ref"):
                    items.append({k: row.get(k, "") for k in ("name", "desc", "qty", "ref", "notes")})
            i += 1
            continue
        cols = None if not s.startswith("|") else cols
        # snippet blocks
        m = re.match(r"^-\s*item\s*:\s*(.*)$", s, re.I)
        if m:
            cur = {"name": m.group(1).strip(), "desc": "", "qty": "1", "ref": "", "notes": ""}
            items.append(cur)
        elif cur is not None and raw.startswith((" ", "\t")) and ":" in s:
            k, v = _kv(s)
            if k in ITEM_KEYS:
                cur[ITEM_KEYS[k]] = v
        elif s:
            cur = None
        i += 1
    if not header:
        warnings.append("no ```order header block found: using defaults")
    return {"header": header, "items": items, "warnings": warnings}


def overrides(notes: str) -> dict:
    out = {}
    for part in re.split(r"[;\n]", notes or ""):
        m = re.match(r"^\s*([a-z_]+)\s*=\s*(.+?)\s*$", part)
        if m and m.group(1) in DEFAULTS:
            out[m.group(1)] = m.group(2)
    return out


def _slug(s):
    s = re.sub(r"\.(png|jpe?g|webp|gif|bmp)$", "", str(s).strip().lower())
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def load_order(path) -> dict:
    path = Path(path)
    parsed = parse(path.read_text(encoding="utf-8", errors="replace"))
    settings = {**DEFAULTS, **parsed["header"]}
    if settings["engine"] == "threejs" and "facing" not in parsed["header"]:
        settings["facing"] = "+z"
    project = settings["project"]
    refs_dir = ROOT / settings.get("refs", f"WorkOrders/{project}/refs/")
    warnings = list(parsed["warnings"])
    items, seen = [], set()
    for n, it in enumerate(parsed["items"], 1):
        name = _slug(it["name"]) or (_slug(it["ref"]) if it["ref"] else f"item_{n}")
        if name in seen:
            warnings.append(f"duplicate item name {name!r}")
        seen.add(name)
        try:
            qty = max(1, int(re.sub(r"\D", "", it["qty"]) or 1))
        except ValueError:
            qty = 1
        eff = {**settings, **overrides(it["notes"])}
        ref = it["ref"].strip()
        ref_path = None
        if ref:
            p = (refs_dir / ref)
            ref_path = str(p.relative_to(ROOT)) if p.exists() else None
            if not p.exists():
                warnings.append(f"{name}: reference image not found: {p.relative_to(ROOT) if p.is_relative_to(ROOT) else p}")
        elif settings["route"].upper().startswith("A"):
            warnings.append(f"{name}: route A item without a reference image")
        items.append({"n": n, "name": name, "desc": it["desc"], "qty": qty, "ref": ref, "ref_path": ref_path,
                      "notes": it["notes"], "settings": eff})
    total = sum(it["qty"] for it in items)
    return {"file": str(path), "settings": settings, "items": items, "total_models": total,
            "big_order": total >= BIG_ORDER, "warnings": warnings}


def sprite_specs(settings: dict, ppu=None) -> list:
    """deliver(..., sprites=...) dicts for an item's effective settings (empty if sprites are off)."""
    if str(settings.get("sprites", "no")).lower() not in ("yes", "true", "1"):
        return []
    outline = settings.get("sprite_outline", "dark")
    spec = {"size": int(settings.get("sprite_size", 64)), "outline": None if outline == "none" else outline,
            "rotations": int(settings.get("sprite_rotations", 1))}
    if ppu:
        spec["ppu"] = ppu
    return [{"view": v.strip(), **spec} for v in settings.get("sprite_views", "right").split(",") if v.strip()]


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    plan = load_order(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps(plan, indent=1))
        return
    s = plan["settings"]
    print(f"project {s['project']}  route {s['route']}  engine {s['engine']} (facing {s['facing']})  "
          f"surface {s['surface']}/{s['texture']}  detail {s['detail']}")
    print(f"glb {s['glb']}  sprites {s['sprites']}" + (
        f"  views {s['sprite_views']} size {s['sprite_size']} outline {s['sprite_outline']} "
        f"same-scale {s['sprite_same_scale']} rotations {s['sprite_rotations']}" if s["sprites"] == "yes" else ""))
    print(f"palette: {s['palette']}")
    for it in plan["items"]:
        ov = overrides(it["notes"])
        print(f"  {it['n']:>3}. {it['name']:<24} x{it['qty']:<3} ref={it['ref'] or '-':<18} {it['desc'][:60]}"
              + (f"  overrides={ov}" if ov else ""))
    print(f"{len(plan['items'])} items, {plan['total_models']} models"
          + ("  -> big order: archetype generators + grid reviews, PROGRESS.md" if plan["big_order"] else ""))
    for w in plan["warnings"]:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
