"""Feasibility test 4: 3-storey townhouse (Walls/Roofs/City blocks) with tinted 128px SurfaceTex textures.

Wall blocks occupy the -z edge of a 1x1 cell centred on their pivot. Rotations that face each side
outward: back(-z)=0, left(-x)=90, front(+z)=180, right(+x)=270. Quoins sit on the (-x,+z) corner at 0.
"""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

SX, SZ, FLOORS = 4, 3, 3
m = Model()
m.mat("brick", "#C9673F", texture="S128 Built/s128_bui_116.png")
m.mat("trim", "#E8DCC4", texture="S128 Natural/s128_nat_98.png")
m.mat("plinth", "#6B6F78", texture="S128 Natural/s128_nat_861.png")
m.mat("roof", "#55585F")
m.mat("glass", "#9FD8F0", gloss=0.9)
m.mat("door", "#3F6E4E")
m.mat("metal", "#3A3D45")
pal = {"stone": "brick", "stoneDark": "plinth", "stoneLight": "trim", "glass": "glass",
       "wood": "door", "woodDark": "door", "metalDark": "metal", "metal": "metal", "dark": "metal"}

def side_cells():
    for x in range(SX):
        yield (x, 0), 0, (x, -1)           # back
        yield (x, SZ - 1), 180, (x, SZ)    # front
    for z in range(SZ):
        yield (0, z), 90, (-1, z)          # left
        yield (SX - 1, z), 270, (SX, z)    # right

for f in range(FLOORS):
    for (x, z), rot, (ox, oz) in side_cells():
        front = rot == 180
        if f == 0:
            block = "Walls/doorway_doorWoodWindow" if front and x == 1 else (
                "Walls/window_squareGlassLarge" if front and x == 2 else "Walls/wall_border")
            ground = {"stone": "plinth"} if block == "Walls/wall_border" else {}
            m.add(block, (x, f, z), (0, rot, 0), recolor={**pal, **ground})
        else:
            window = (x if rot in (0, 180) else z) % 2 == 1 or (rot in (90, 270) and SZ == 3 and z == 1)
            m.add("Walls/window_squareGlass" if window else "Walls/wall", (x, f, z), (0, rot, 0), recolor=pal)
            if front and window and f == 1:
                m.add("City/balcony_basic", (ox, f, oz), (0, rot + 180, 0), recolor=pal)
        if f == FLOORS - 1:
            m.add("Walls/cornice_extended", (ox, f + 0.25, oz), (0, rot + 180, 0), recolor=pal)
    for (x, z), rot in (((0, SZ - 1), 0), ((SX - 1, SZ - 1), 90), ((SX - 1, 0), 180), ((0, 0), 270)):
        m.add("Walls/quoin_detailed", (x, f, z), (0, rot, 0), recolor=pal)

for x in range(SX):
    for z in range(SZ):
        m.add("Roofs/roof_flat", (x, FLOORS, z), recolor={"stone": "roof"})
m.add("City/roof_windowGlass", (1, FLOORS + 0.1, 1), recolor=pal)
m.add("City/detail_ventSmall", (3, FLOORS + 0.1, 0), (0, 30, 0), recolor=pal)

here = ROOT / "Workbench" / "examples"
deliver(m, "townhouse", here, ROOT / "Assets" / "examples",
        sprites=[{"view": "front", "size": 96, "upscale_preview": 4},
                 {"view": "iso", "size": 128, "upscale_preview": 3}])
