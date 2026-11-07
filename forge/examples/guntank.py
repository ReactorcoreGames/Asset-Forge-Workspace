"""Feasibility test 5: Guntank-style flying mech-tank mixing 3 collections.

  Zenith_TrackTanks (custom) - tracked hull, shoulder cannon barrels
  Mech (built-in)            - pelvis, chest, head, shoulders, arm sockets, fists
  Aircraft (built-in)        - wings + back thrusters for the flight mode
Groups are named so a game can animate them (turret_upper, arm_l/r, cannon_l/r, wings).
"""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver

Z = "Zenith_TrackTanks/"
m = Model()
m.mat("blue", "#2F5DB8", metallic=0.2, gloss=0.4)
m.mat("white", "#E9ECF2", gloss=0.4)
m.mat("red", "#D83A2E", gloss=0.4)
m.mat("yellow", "#F2C230")
m.mat("dark", "#2B2D36")
m.mat("visor", "#7CF0C8", gloss=0.9)
pal = {
    "zenith_tracktanks-blueSteel": "blue", "zenith_tracktanks-orangeSteel": "white",
    "zenith_tracktanks-_defaultMat": "white", "zenith_tracktanks-tire": "dark",
    "zenith_tracktanks-None": "dark", "zenith_tracktanks-glass": "visor",
    "metalOrange": "blue", "_defaultMat": "white", "dark": "dark", "metalPurple": "red",
    "metalLight": "white", "shield": "visor",
}

# --- tracked lower hull (Zenith), widened 1.4x
W, HY = 1.4, 0.18
m.add(Z + "01 Tank Body 01", (0, HY, 0), scale=(W, 1, 1), recolor=pal, group="hull")
m.add(Z + "01 Tank Body Front 01", (0, HY, 1.0), scale=(W, 1, 1), recolor=pal, group="hull")
m.add(Z + "01 Tank Body Back 01", (0, HY, -1.0), scale=(W, 1, 1), recolor=pal, group="hull")
m.add(Z + "01 Simplified track 01", (-0.3, 0, 0), scale=(1.4, 1.2, 3.3), recolor=pal, group="tracks", mirror=True)
# running gear inside the track loops: 5 road wheels + larger sprocket/idler at each end
for z in (-0.95, -0.47, 0.0, 0.47, 0.95):
    m.add(Z + "02 Car Body wheel 03", (-0.5, 0.2, z), scale=0.55, recolor=pal, group="tracks", mirror=True)
for z in (-1.3, 1.3):
    m.add(Z + "02 Car Body wheel 01", (-0.42, 0.24, z), scale=(0.5, 0.62, 0.62), recolor=pal, group="tracks", mirror=True)
m.add(Z + "01 Tank Body Track cover 03", (0.45, 0.05, 0.6), scale=(1, 1, 1.4), recolor={**pal, "zenith_tracktanks-orangeSteel": "red"}, group="hull", mirror=True)
m.add(Z + "01 Tank Body Track cover 03", (0.45, 0.05, -0.6), scale=(1, 1, 1.4), recolor={**pal, "zenith_tracktanks-orangeSteel": "red"}, group="hull", mirror=True)

# --- mech upper body (Mech), rotates as one turret
top = HY + 0.5
m.add("Mech/pelvis_belt", (0, top, 0), scale=1.2, recolor=pal, group="turret_upper")
chest_y = top + 0.45
m.add("Mech/chest_shoulders", (0, chest_y, 0), scale=1.15, recolor=pal, group="turret_upper")
m.add("Mech/head_marine", (0, chest_y + 1.15, 0.05), recolor=pal, group="turret_upper")
for side, sx in (("r", 1), ("l", -1)):
    sh_y = chest_y + 0.6
    m.add("Mech/shoulder_default", (0.5 * sx, sh_y, 0), scale=(sx, 1, 1), recolor={**pal, "metalOrange": "red"}, group=f"arm_{side}")
    m.add("Mech/socket_medium", (0.78 * sx, sh_y - 0.3, 0), (0, 0, 90), scale=1.3, recolor=pal, group=f"arm_{side}")
    m.add("Mech/socket_medium", (0.78 * sx, sh_y - 0.62, 0.2), (0, 90, 0), scale=1.2, recolor=pal, group=f"arm_{side}")
    m.add("Mech/hand_closed", (0.78 * sx, sh_y - 0.62, 0.45), scale=(sx * 1.2, 1.2, 1.2), recolor=pal, group=f"arm_{side}")
    # twin shoulder cannons (Zenith barrels) on top of the shoulders
    m.add(Z + "01 Tank Barrel 02", (0.72 * sx, sh_y + 0.55, 0.25), scale=(1.6, 1.6, 1.8), recolor={**pal, "zenith_tracktanks-orangeSteel": "yellow"}, group=f"cannon_{side}")
    m.add("Mech/weapon_turretSmall", (0.72 * sx, sh_y + 0.42, -0.05), scale=0.7, recolor=pal, group=f"cannon_{side}")

# --- flight pack (Aircraft): wings + thrusters on the back
back_z = -0.62
m.add("Aircraft/wing_slantWinglet", (-1.15, chest_y + 0.55, back_z), (0, 0, -10), scale=(1.3, 1, 1.1), recolor={**pal, "metalPurple": "red"}, group="wings", mirror=True)
m.add("Aircraft/engine_turbineRounded", (-0.32, chest_y + 0.2, back_z - 0.1), scale=0.5, recolor={**pal, "metalPurple": "blue"}, group="thrusters", mirror=True)

here = ROOT / "Workbench" / "examples"
deliver(m, "guntank_flyer", here, ROOT / "Assets" / "examples",
        sprites=[{"view": "right", "size": 64, "upscale_preview": 6},
                 {"view": "iso", "size": 96, "upscale_preview": 4}])
