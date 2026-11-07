"""Kitbash test: a small silo mixing RC_Primitives with built-in Primitives (slots, pivots, facing)."""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

here = Path(__file__).parent
m = Model()
m.mat("grass", "#6BAF4B")
m.mat("rock", "#8A7B6A")
m.mat("concrete", "#A9A9A4")
m.mat("paint", "#D8D2C0")
m.mat("trim", "#C2452D", metallic=0.3, gloss=0.5)
m.mat("dark", "#2E3138")
m.mat("glow", "#FFD35A")
RC = "RC_Primitives/"

# ground: RC hill tile with its ground skirt as grass, the mound as rock (tests the `ground` slot)
m.add(RC + "hill_10", (0, 0, 0), scale=(5, 0.6, 5),
      recolor={"rc_primitives-ground": "grass", "rc_primitives-base": "rock"}, group="ground")
# built-in bevelled plinth sitting on the hill top (hill_10 is 0.5 tall -> 0.3 at scale 0.6)
m.add("Primitives/block_bevel", (0, 0.3, 0), scale=(2.4, 0.3, 2.4), recolor={"_defaultMat": "concrete"})
# built-in wedge as an access ramp: high side at -z butts the plinth's front face (z = 1.2)
m.add("Primitives/wedge", (0, 0.12, 1.75), scale=(0.8, 0.48, 1.1), recolor={"_defaultMat": "concrete"})
# RC tank: barrel + torus band + dome cap, all bottom-centre so they stack by height
m.add(RC + "barrel_16sided", (0, 0.6, 0), scale=(1.6, 2.0, 1.6), recolor={"rc_primitives-base": "paint"}, group="tank")
m.add(RC + "torus", (0, 1.4, 0), scale=(1.72, 1.0, 1.72), recolor={"rc_primitives-base": "trim"}, group="tank")
m.add(RC + "dome_doublesided", (0, 2.6, 0), scale=(1.6, 1.2, 1.6),
      recolor={"rc_primitives-base": "trim", "rc_primitives-inner": "dark"}, group="tank")
# door: built-in block, front of the tank (+z)
m.add("Primitives/block", (0, 0.6, 0.76), scale=(0.45, 0.75, 0.1), recolor={"_defaultMat": "dark"}, group="tank")
# antenna: built-in cylinder mast + RC icosphere beacon
m.add("Primitives/cylinder", (0, 3.2, 0), scale=(0.08, 0.9, 0.08), recolor={"_defaultMat": "dark"}, group="antenna")
m.add(RC + "icosphere_0080", (0, 4.05, 0), scale=(0.22, 0.22, 0.22), recolor={"rc_primitives-base": "glow"}, group="antenna")
# RC cone spikes on the plinth corners
for x in (-0.95, 0.95):
    for z in (-0.95, 0.95):
        m.add(RC + "cone_08sided", (x, 0.6, z), scale=(0.25, 0.5, 0.25), recolor={"rc_primitives-base": "trim"})

deliver(m, "rc_silo_test", here, here)
