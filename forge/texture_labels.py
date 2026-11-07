"""Hand-reviewed category labels (visual pass over Textures/sheets/*_all_*.png, 2026-10-24).

Anything not listed is 'natural'. Rules used:
  natural  - organic/irregular: rock, dirt, sand, grass, bark, raw wood grain, water, marble, grunge, noise
  built    - man-made structure: bricks, cobble walls, tiles, planks/boards, grids, plates, panels, stripes
  abstract - designed/ornamental: lace & fabric motifs, mandalas, checkers, gradients, camo, bokeh, stars
Run `python forge/texture_labels.py` to regenerate Textures/overrides.json, then `textures.py classify`.
"""
import json
from pathlib import Path


def expand(spec):
    out = set()
    for part in spec.replace("\n", " ").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        else:
            out.add(int(part))
    return out


LABELS = {
    "micro32": {
        "built": """32,39,49,183,199,319,326,338,350,396,410,423,426,465,480,484,486,487,492,493,497-503,
            508-510,512-514,522,530,532-536,547,549-552,559-564,567,571,572,574,575,578,583-588,593,594,601,
            609,611,629,631,719-723,728,763-774,782,785,786,823-826,828,831,832,871-879,881,883,887,981,991,
            994,1000,1024,1043,1084,1140,1150-1152,1154,1155,1157,1161""",
        "abstract": """3,4,9,10,15,17-19,22,24,25,28,31,37,38,43,44,54,64,66,84-87,100-103,107-109,117-120,
            123-125,127,131-137,139-148,151-153,155-159,164-169,173-178,181,182,184,185,187,189,192,196-198,
            200,203,204,207-211,213-219,225-231,233,235-238,242,243,247-250,252-256,258,259,261,262,264-269,
            275,285,286,288,290,291,295,296,298,299,301,308-310,313,318,321-325,327-329,333-337,339-341,
            344-346,352,355,357,361-364,366-375,377,379,380,383-386,389-393,399-404,416,419,425,428,429,
            432-436,439,440,443-449,451,452,455,456,459,462,466-468,470-474,596,739,750,760,775-777,780,781,
            793,803-805,816,827,833,834,849,860,869,880,886,891,905-909,913,919,922,923,925,926,929,936,947,
            957,960-969,976-978,985,1007-1018,1026-1034,1036-1041,1045,1047-1052,1055-1058,1065,1066,
            1069-1071,1073,1075,1082,1083,1088-1103,1105,1107-1110,1112-1121,1123-1131,1134-1139,1143-1148,
            1158,1164""",
    },
    "surf128": {
        "built": """7,26,27,44,52,61,68,86,87,96,104,116,133,149,162,165,168,169,183,186,187,189,207,208,
            212,217,221,238,239,266,268,270,274,351,367,413,594,602,603,639,685,694-699,701-704,707,708,713,
            716,744,745,773,774,821,825,857,862-864,868-870,877-880,889-893,900""",
        "abstract": """9,10,17-19,33,35,36,43,53,59,62,63,69,71,78-80,89,97,99,106,113,115,122,132,148,176,
            223,250-260,267,315,328,372-412,415-435,438-454,456-470,472-479,481-484,486-531,533,541,542,544,
            550,551,553,554,556-558,560,561,563,567-571,581,584,585,595-601,604-619,636-638,640,641,643-650,
            653-666,669-671,673-683,684,686-692,719-736,738-740,743,747-759,766-769,779,790-793,801,802,804,
            806,808,810-814,819,840-850,854-856,871-873,881-884,894,895,901""",
    },
}


def overrides():
    out = {}
    from textures import PACKS
    for pack, cats in LABELS.items():
        folder, pattern, _ = PACKS[pack]
        files = sorted(folder.glob(pattern), key=lambda p: (len(p.stem), p.stem))
        for i, p in enumerate(files):
            cat = "natural"
            for c in ("built", "abstract"):
                if i in expand(cats[c]):
                    cat = c
            out[f"{pack}/{p.name}"] = cat
    return out


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    ov = overrides()
    dst = Path(__file__).resolve().parent.parent / "Textures" / "overrides.json"
    dst.write_text(json.dumps(ov, indent=0))
    print(f"wrote {len(ov)} labels -> {dst}")
