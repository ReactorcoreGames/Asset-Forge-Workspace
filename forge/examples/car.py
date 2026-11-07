"""Feasibility test 1: sports car from Vehicles blocks (layout follows Kenney's carGenerator.lua)."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

h, w, fs = 0.12, 1.15, 0.95          # ride height drop, body width, bonnet length
m = Model()
m.mat("paint", "#D7263D", metallic=0.3, gloss=0.6)
m.mat("trim", "#1E1E24")
m.mat("chrome", "#C9CCD6", metallic=0.6, gloss=0.7)
m.mat("stripe", "#F2F2F2")
paint = {"metalGreen": "paint", "metalLight": "chrome", "metal": "stripe"}

m.add("Vehicles/body_frontSports", (0, -h, 0.5 + fs / 2), scale=(w, 1, fs), recolor=paint, group="body")
m.add("Vehicles/body_sports", (0, -h, 0), scale=(w, 1, 1), recolor=paint, group="body")
m.add("Vehicles/body_backFins", (0, -h, -1), scale=(w, 1, 1), recolor=paint, group="body")
m.add("Vehicles/body_topSports", (0, 1 - h, 0), scale=(1, 0.75, 1), recolor=paint, group="body")
m.add("Vehicles/body_topBackSport", (0, 1 - h, -1), scale=(1, 0.75, 1), recolor=paint, group="body")
m.add("Vehicles/spoiler_fins", (0, 1 - h, -1.25), recolor=paint, group="body")
m.add("Vehicles/bumper_detailed", (0, 0.3, 0.4 + fs / 2), recolor=paint, group="body")
m.add("Vehicles/bumper", (0, 0.3, -1), rot=(0, 180, 0), recolor=paint, group="body")
m.add("Vehicles/detail_mirror", (-0.5 - w / 2, 0.9 - h, 0.5), recolor=paint, group="body")
m.add("Vehicles/detail_mirror", (0.5 + w / 2, 0.9 - h, 0.5), scale=(-1, 1, 1), recolor=paint, group="body")
for z, tag in ((-0.75, "rear"), (0.4 + fs / 2, "front")):
    m.add("Vehicles/wheel_spokes", (-0.5, 0.3, z), rot=(0, 180, 0), recolor=paint, group=f"wheel_{tag}_l")
    m.add("Vehicles/wheel_spokes", (0.5, 0.3, z), recolor=paint, group=f"wheel_{tag}_r")
    m.add("Vehicles/wheel_coverStandard", (-1, 0.3, z), rot=(0, 180, -5), recolor=paint, group="body")
    m.add("Vehicles/wheel_coverStandard", (1, 0.3, z), rot=(0, 0, -5), recolor=paint, group="body")

here = ROOT / "Workbench" / "examples"
deliver(m, "sports_car", here, ROOT / "Assets" / "examples",
        sprites=[{"view": "right", "size": 64, "upscale_preview": 6},
                 {"view": "top", "size": 48, "upscale_preview": 6}])
