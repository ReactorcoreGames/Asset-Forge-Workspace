"""Feasibility test 2: arcade spaceship (built-in Aircraft blocks, 1-unit grid, pivot bottom-centre)."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

m = Model()
m.mat("hull", "#EDEFF5", gloss=0.5)
m.mat("accent", "#FF6A1A", metallic=0.2, gloss=0.6)
m.mat("canopy", "#2FD4FF", gloss=0.9)
m.mat("dark", "#2A2C38")
pal = {"_defaultMat": "hull", "metalPurple": "accent", "shield": "canopy", "metalLight": "hull"}

m.add("Aircraft/hull_cockpitPoint", (0, 0, 1), recolor=pal)
m.add("Aircraft/hull_body", (0, 0, 0), recolor=pal)
m.add("Aircraft/hull_topEngine", (0, 1, -1), recolor=pal)
m.add("Aircraft/hull_tail", (0, 0, -1), recolor=pal)
m.add("Aircraft/wing_slantWinglet", (-1, 0.3, -0.5), recolor=pal, mirror=True)
m.add("Aircraft/wing_slant", (-1, 0.3, 0.5), scale=(1, 1, 0.8), recolor=pal, mirror=True)
m.add("Aircraft/engine_turbineRounded", (-1.75, 0.15, -0.6), scale=0.55, recolor=pal, mirror=True)
m.add("Aircraft/rudder_angle", (-0.35, 1.0, -1.2), recolor=pal, mirror=True)

here = ROOT / "Workbench" / "examples"
deliver(m, "arcade_fighter", here, ROOT / "Assets" / "examples",
        sprites=[{"view": "top", "size": 48, "upscale_preview": 8},
                 {"view": "right", "size": 48, "upscale_preview": 8}])
