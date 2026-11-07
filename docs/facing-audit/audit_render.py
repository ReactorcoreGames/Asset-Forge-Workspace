"""Facing audit: render chosen blocks in the 'right' view (front should point screen-right)."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:/ClaudeWorkspace/Asset-Forge-Workspace/forge")
import forge
from PIL import Image, ImageDraw

OUT = Path(sys.argv[1])
VIEW = sys.argv[2] if len(sys.argv) > 2 else "right"
SETS = {
 "REF_builtin": ["Vehicles/body_frontSports", "Aircraft/hull_cockpitNose", "Blasters/blaster_back", "Blasters/blaster_barrel", "Characters/head_default", "Mech/hand_closed", "Animals/body_point", "Vehicles/body_backStandard"],
 "Azeus_Blasters": ["barrel_simple", "barrel_back_round", "blaster_front_alienFlower", "largeBlaster_front_shark",
                    "largeBlaster_center", "grip_trigger_viper_1a", "ironsight_front_coyote", "bayonet_long",
                    "stock_", "scope_"],
 "Azeus_RocketLaunchers": ["front_001", "front_005", "back_001", "back_005", "middle_001", "rocket_001", "grip_trigger_001", "scope_001"],
 "K_Cars": ["sedan", "police", "truck", "tractor", "race", "van"],
 "K_CityScape": ["low_buildingA", "small_buildingA", "large_buildingA", "wall_doorA", "detail_awning", "sign_billboard"],
 "K_Cityroad": ["road_end", "road_sideEntry", "light_curved", "construction_barrier", "road_bend", "road_bridge"],
 "K_NatureKit": ["bed", "canoe", "fence_gate", "tent_", "sign", "statue_", "bridge_wood", "campfire_logs"],
 "K_Spacebase": ["craft_racer", "craft_speederA", "craft_cargoA", "rover", "astronautA", "alien", "monorail_trainFront", "desk_computer", "turret_single", "weapon_rifle", "hangar_smallA", "corridor_end"],
 "K_UrbanHouses": ["house_type01", "house_type05", "house_type10", "driveway_long", "fence_gate", "path_long"],
 "Keith_ModularTerrain": ["Cave_Prop_Minecart_1", "Beach_Prop_Treasure_Chest", "Beach_Prop_Docks_Steps", "Cave_Prop_Railway_Bumpstop", "Beach_Terrain_Sand_Side_Gentle", "Cave_Prop_Entrance_1"],
 "Keith_Spaceships": ["Cockpit_Model_A", "Cockpit_Model_B_End_1", "Hyperdrive_Rearmount_Large", "Thruster_Triple_Large", "Fuselage_Narrow_Front$", "Bay_Door"],
 "Zenith_HyperStarships": ["Bridge01$", "Cabin01$", "Cabin05$", "Engine01$", "Engine09$", "Weapon01$", "Canard01$", "Cap01$", "Hull01$", "Wing01$"],
 "Zenith_TrackTanks": ["Tank Body Front 01", "Tank Body Back 01", "Tank Barrel 01", "turret 01", "02 Car Body front 01", "02 truck cockpit 01",
                       "03 Buggy Front 01", "03 Buggy cockpit", "04 Monorail Cart Cockpit", "05 cockpit 01", "05 Tail 01", "06 Excavator"],
}
lib = forge.library()["blocks"]
T = 160
for name, pats in SETS.items():
    if len(sys.argv) > 3 and name not in sys.argv[3:]:
        continue
    keys = []
    for p in pats:
        if "/" in p:
            hits = [p] if p in lib else []
        else:
            hits = forge.find(p, name)[:1]
        keys += hits
    cols = 4
    rows = (len(keys) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * T, rows * (T + 14)), (24, 25, 29))
    d = ImageDraw.Draw(sheet)
    for i, k in enumerate(keys):
        m = forge.Model(); m.add(k)
        im = forge.render(m.assemble(), None, T, VIEW, bg="#34363D")
        x, y = (i % cols) * T, (i // cols) * (T + 14)
        sheet.paste(im, (x, y))
        b = lib[k]
        d.text((x + 2, y + T), k.split("/", 1)[1][-24:], fill=(230, 230, 230))
        d.text((x + 2, y + 2), f"z {b['min'][2]:.2f}..{b['max'][2]:.2f}", fill=(255, 200, 80))
    sheet.save(OUT / f"{name}_{VIEW}.png")
    print(name, keys)
