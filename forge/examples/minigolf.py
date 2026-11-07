"""Feasibility test 3: minigolf hole (Golf blocks on a 1-unit grid) with tinted 32px Microart textures.

Connection rules (from Kenney's golfGenerator.lua): straights run along +z at rot 0 and along +x at
rot 90; 'bend' at rot 0 turns +z -> +x, at rot 180 turns +x -> +z; the goal piece is rotated +180.
"""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

m = Model()
m.mat("turf", "#5BC24A", texture="M32 Natural/m32_nat_597.png")
m.mat("border", "#E0734F", texture="M32 Built/m32_bui_567.png")
m.mat("timber", "#9A6A44", texture="M32 Natural/m32_nat_614.png")
m.mat("cloth", "#F4F1E8")
pal = {"foliage": "turf", "bricks": "border", "wood": "timber", "_defaultMat": "cloth"}

course = [  # (block, x, z, rot_y)
    ("Golf/start", 0, 0, 0),
    ("Golf/straight", 0, 1, 0),
    ("Golf/straight_obstacleRound", 0, 2, 0),
    ("Golf/bend", 0, 3, 0),
    ("Golf/straight", 1, 3, 90),
    ("Golf/bump", 2, 3, 90),
    ("Golf/straight_hill", 3, 3, 90),
    ("Golf/bend", 4, 3, 180),
    ("Golf/straight", 4, 4, 0),
    ("Golf/straight_narrowSquare", 4, 5, 0),
    ("Golf/end_hole", 4, 6, 180),
]
for block, x, z, r in course:
    m.add(block, (x, 0, z), (0, r, 0), recolor=pal)

m.add("Golf/building_windmill", (4, 0.2, 5.15), recolor=pal, group="windmill")
m.add("Golf/building_windmillWicks", (4, 0.72, 4.84), (0, 0, 20), recolor=pal, group="windmill_wicks")
m.add("Fences/poles_garlandFlags", (1, 0.2, 3), (0, 90, 0), recolor=pal)
m.add("Fences/poles_garlandFlags", (0, 0.2, 1), recolor=pal)
m.add("Golf/detail_flag", (4.15, 0.2, 6.1), recolor=pal, group="flag")

here = ROOT / "Workbench" / "examples"
deliver(m, "minigolf_hole", here, ROOT / "Assets" / "examples",
        sprites=[{"view": "top", "size": 96, "upscale_preview": 4},
                 {"view": "dimetric", "size": 128, "upscale_preview": 3}])
