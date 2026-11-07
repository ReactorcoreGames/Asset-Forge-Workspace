# Custom collection facing audit (2026-10-24)

Reference: Asset Forge's built-in blocks face **+z** (`sheets/REF_builtin_right.png`: in the `right` view the car bonnet, cockpit nose and mech hand all point screen-right). Each custom collection was checked by rendering its directional pieces alone in the `right`, `front`, `back` and `top` views (scripts: `audit_render.py`, `audit_all.py`, `fb.py`; evidence sheets kept locally in `old wip/Workbench/_facing-audit/sheets/`). In the `front` view the camera looks at the +z face; in `back` it looks at the −z face.

## Applied 2026-10-24: rotated 180° about Y (vertices + normals)

Approved by the user and applied with `forge/rotate_collection.py`. Originals are backed up in `C:\trash\collections-original\`. Library re-extracted and catalogue rebuilt afterwards. Post-fix checks: in `library.json`, 118 blocks have exactly mirrored x/z bounds and the rest are unchanged or symmetric, with slot lists and triangle counts untouched. The guntank rebuilt without its rot 180 is pixel-identical to before. The local `sheets/after_*.png` show the fronts now on +z.

| collection | evidence | scope |
|---|---|---|
| K_CityScape | shopfronts, glass doors and awning stripes are all on the −z face; the +z face is plain (`kcs_front.png` vs `kcs_back.png`) | whole collection (56 OBJs) |
| K_UrbanHouses | front doors with handles, garages, porches and dormers are on −z; +z has plain back doors (`kuh_front.png` vs `kuh_back.png`) | whole collection (36 OBJs) |
| Zenith_HyperStarships | cockpit glass on −z, engine nozzles glow on +z, cabins/bridges/canards/wings/gun barrels all point −z (`zhs_fb.png`, `zhs_top.png`) | whole collection (145 OBJs) |
| Zenith_TrackTanks | **mixed by vehicle series**: tank (01), car/truck (02) and buggy (03) pieces face −z; bus (02), monorail (04), aircraft (05) and the attachments face +z (`ztt_*.png`) | 24 OBJs, listed below |

Zenith_TrackTanks, rotated (series rotated as a unit so their pieces still fit each other):

- 01 tank: `Tank Body 01`, `Tank Body Front 01–04`, `Tank Body Back 01–02`, `Tank Body turret 01–03`, `Tank Barrel 01` (points −z from turret 01's slot), `RocketPod` (tubes open on −z)
- 02 car/truck: `Car Body front 01`, `Car Body Back 01–02`, `truck cockpit 01` (windscreen on −z), `truck front 01` (headlights on −z)
- 03 buggy: `Buggy Front 01–02`, `Buggy cockpit 01`, `Buggy hood 01`, `Buggy Back 01`, `engine 01`, `Car Trailer`

Zenith_TrackTanks, unchanged: already +z: `Tank Barrel 02` (muzzle +z), `snowplow` and `Car Bumper 01–03` (blades face +z and sit beyond the +z edge), `Bus Front/Middle/Back 01` (windscreen on +z), `Monorail Cart Cockpit/Passenger 01`, all `05` aircraft pieces (nose +z, tail fin −z). Non-directional: `Barrel`, `roller`, `Simplified track`, `Tracks 01/01obj/02/03`, `Track cover 02/03`, `Car Body wheel 01–03`, monorail track pieces. Ambiguous: `06 Excavator Bucket`.

## Already +z (no change)

- Azeus_Blasters: muzzles, bayonets and `*_front` pieces extend +z, stocks and `barrel_back_*` sit at −z.
- Azeus_RocketLaunchers: `front_*` extend +z, `back_*` extend −z, rockets point +z.
- K_Cars: cabs and bonnets toward +z (tractor's small front wheels at +z).
- K_Spacebase: crafts, rover, astronauts, monorail front and desk screens face +z.
- K_NatureKit: mostly non-directional; bed foot, sign board and fence gate face +z.

## Non-directional (no change)

Hexagon, Quaternius_Crops, Quaternius_Nature.

## Mixed or ambiguous (left alone)

- **Keith_Spaceships**: modules are built along the **x** axis, not z (the `right` view shows the octagonal cross-section). The cockpit windows face +x, but nose cones (`Fuselage_Narrow_Front`, `Housing_Front`) point −x, so there is no single front. A 90° fix would be a guess.
- **Keith_ModularTerrain**: terrain tiles have no front; props disagree (treasure chest lock on −z, railway bumpstop buffer facing +z).
- **K_Cityroad**: road tiles are non-directional; street-light arms overhang −z, but there is no "front" convention to match.
