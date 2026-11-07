"""RC_Primitives vs built-in Primitives: each tile = built-in (warm, left) and RC (cool, right), same pivot, on a floor slab."""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, review_grid, block_info

here = Path(__file__).parent
PAIRS = [  # (built-in, rc, rc scale)
    ("block", "cube", 1), ("cylinder", "cylinder_32sided", 1), ("cone", "cone_32sided", 1),
    ("sphere", "sphere_16x16", 1), ("icosphere", "icosphere_0080", 1), ("sphere_half", "dome_external", 1),
    ("sphere_quarter", "dome_quarter_external", 1), ("cylinderHollow_half", "ring_half_external", 1),
    ("cylinder_quarter", "ring_quarter_external", 1), ("halfPipe", "half_pipe", 1),
    ("halfPipe_half", "ramp_round_01", 1), ("wedge", "ramp_01", 2), ("roof", "ramp_02", 2),
    ("wedge_cornerOuter", "ramp_03", 2), ("diamond", "shard_01", 1), ("cross", "cross_01", 1),
    ("blockTriangle", "cylinder_03sided", 1), ("pyramid", "cone_04sided", 1),
]


def pair(b, r, sy):
    m = Model()
    m.mat("builtin", "#E08A5A")
    m.mat("rc", "#6FA8DC")
    m.mat("rc_in", "#2F5E8C")
    m.mat("floor", "#55585F")
    m.add("Primitives/block", (0, -0.03, 0), scale=(2.6, 0.03, 1.3), recolor={"_defaultMat": "floor"})
    m.add(f"Primitives/{b}", (-0.65, 0, 0), recolor={s: "builtin" for s in block_info(f"Primitives/{b}")["slots"]})
    m.add(f"RC_Primitives/{r}", (0.65, 0, 0), scale=(1, sy, 1),
          recolor={"rc_primitives-base": "rc", "rc_primitives-inner": "rc_in", "rc_primitives-ground": "rc"})
    return m


items = [(f"{b} | {r}" + (f" y{sy}" if sy != 1 else ""), pair(b, r, sy)) for b, r, sy in PAIRS]
for view in ("iso", "right", "top"):
    review_grid(items, here / f"compare_{view}.png", size=200, cols=6, view=view)

# half pipe + end cap on the grid: pipe at z=0, cap at z=1 (should butt with no gap)
m = Model()
m.mat("rc", "#6FA8DC")
for z in (-1, 0):
    m.add("RC_Primitives/half_pipe", (0, 0, z), recolor={"rc_primitives-base": "rc"})
m.add("RC_Primitives/half_pipe_end", (0, 0, 1), recolor={"rc_primitives-base": "rc"})
review_grid([("pipe z-1,0 + end z1 iso", m), ("same, right", m)], here / "halfpipe_iso.png", size=260, cols=2)
review_grid([("right view", m)], here / "halfpipe_right.png", size=260, cols=1, view="right")
review_grid([("top view", m)], here / "halfpipe_top.png", size=260, cols=1, view="top")
