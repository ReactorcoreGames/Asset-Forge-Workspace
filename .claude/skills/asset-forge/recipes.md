# Placement recipes

Learned from Kenney's generator scripts (`Asset Forge 2.5.3 (Windows)/Scripts/*.lua`), the sample models, and the feasibility builds in `forge/examples/`. All coordinates are Asset Forge space (+Z front, +X right, +Y up).

## General

- Most built-in blocks: 1x1 cell footprint, pivot at **bottom-centre** (`min y = 0`, x/z in ±0.5). Always check `min`/`max` with `forge.py find`, because exceptions are common (walls sit on a cell edge, `wing_long` extends to −x, hands extend +z from the wrist).
- A block that only extends to one side (e.g. `min x = 0`, like `Mech/shoulder_default`) is a right-hand part. Use `scale=(-1,1,1)` or `mirror=True` for the left.
- Custom OBJ collections (Zenith, Keith, K_*, Quaternius, Azeus) use the same ~1-unit scale. Kitbashing across collections works without rescaling.
- **All collections face +z (standardised on 2026-10-24).** Custom OBJs that were authored nose-toward −z were turned 180° about Y in place (vertices + normals, via `forge/rotate_collection.py`; originals in `C:\trash\collections-original\`). Place every directional piece at rot 0 for "forward". Evidence and reasoning are in `docs/facing-audit/AUDIT.md`. What was changed:
  - `K_CityScape`: whole collection (shopfronts were on −z).
  - `K_UrbanHouses`: whole collection (front doors and garages were on −z).
  - `Zenith_HyperStarships`: whole collection (cockpits, canards and guns pointed −z).
  - `Zenith_TrackTanks`: 24 pieces of the 01 tank, 02 car/truck and 03 buggy series (`Tank Body 01`, `Front 01–04`, `Back 01–02`, `turret 01–03`, `Tank Barrel 01`, `RocketPod`, `Car Body front 01`, `Car Body Back 01–02`, `truck cockpit 01`, `truck front 01`, `Buggy Front 01–02`, `Buggy cockpit 01`, `Buggy hood 01`, `Buggy Back 01`, `engine 01`, `Car Trailer`). The bus, monorail, 05 aircraft, bumpers, snowplow and `Tank Barrel 02` already faced +z.
  - Unchanged, already +z: Azeus_Blasters, Azeus_RocketLaunchers, K_Cars, K_Spacebase, K_NatureKit. Non-directional: Hexagon, Quaternius_Crops, Quaternius_Nature.
  - `RC_Primitives`: +z, generated already standardised by `forge/import_collection.py` (see its section below).
  - **Still not standardised (no single front, check before use):** `Keith_Spaceships` is built along the **x** axis (cockpit windows face +x, nose cones point −x), so rotate per piece. `Keith_ModularTerrain` props disagree (chest lock −z, bumpstop buffer +z). `K_Cityroad` tiles have no front. For any piece from these, or from a newly added collection, render it alone (a `turnaround` of a one-block `Model`) and check the `right` view, where the front should point screen-right.
  - New collection: audit it the same way. If it faces −z, run `forge/rotate_collection.py <Collection> [--only stems...]`, then `extract_library.py --custom-only` and `catalogue.py`.
  - Raw OBJ packs that are not yet at Asset Forge scale or pivot (e.g. authored for an engine, centred, 2-unit) go through `forge/import_collection.py <src> --config forge/packs/<pack>.json` instead. It writes standardised copies (scale, pivot, per-piece yaw and neutral slots baked into v/vn) into `Collections/<Name>/` and never touches the source. Copy `forge/packs/rc_primitives.json` as the starting config. Work out each yaw in Asset Forge space by rendering the source pieces next to their built-in counterparts in `right` and `top` views.
- Kitbashed bases look barren if a track or wheel well is left empty. Fill track loops with road wheels plus an end sprocket (`Zenith_TrackTanks/02 Car Body wheel 03` at scale 0.55, five per side), but note that the Zenith wheels are detailed (~15k tris for 14 wheels).
- Scaling a block non-uniformly is normal in Asset Forge (Kenney's car generator does it). Use it to widen hulls and lengthen bonnets rather than hunting for a variant.

## RC_Primitives (Reactorcore's Deluxe Primitives, CC-BY 4.0) - `docs/rc-primitives-test/build.py`

167 grey primitives, generated from the user's own pack by `forge/import_collection.py` with `forge/packs/rc_primitives.json` (the pack's "Deluxe" name has nothing to do with Asset Forge Deluxe, so none are `%` blocks). Rebuild with `--force` rather than editing the OBJs. The source pack is kept in `sources/Deluxe Primitives/obj models`. Scale is the same as the built-ins: `cube` = `Primitives/block` (1×1×1), and spheres, cylinders and cones are 1 unit in diameter. Pivots are bottom-centre on the shape's own axis (n-sided pieces are inscribed in the 1-unit circle, so odd-sided ones don't fill the cell in z). Front = +z, matched piece by piece to the built-ins.

- **Pivot exceptions:** `pit_*` tiles keep their **rim at y=0** (the pit hangs below), so they sit flush with the `hill_*` tiles and the flat `plane_onesided`/`disk_*`. `half_pipe_end` fills the back half of its cell (z −0.5..0): a `half_pipe` at z=k and the end at z=k+1 butt together. Halves sit on +z (`dome_half_*`, `ring_half_*`, `frame_06/07_half`), quarters at (−x,+z), like `cylinder_half`/`sphere_quarter`. `plane_vertical_doublesided` is a billboard standing in the x-y plane through the pivot.
- **Multi-cell pieces:** `ramp_06/07` and `ramp_round_05/07/10` are 2 wide in x. `ramp_08` and `ramp_round_06/08/11` are 2×2, and `ramp_round_02/03` are 2 long in z. `ramp_round_10/11` are 2 tall. `container_05` is 1.41 wide (use scale 0.7 for one cell).
- **Slots:** `rc_primitives-base` (#D0D0D0, everything), `rc_primitives-inner` (#707070: the inside of `_doublesided` pieces, all of `_internal` pieces, and the back of the double-sided plane and triangle), `rc_primitives-ground` (#A0A0A0: the flat skirt of `hill_02..12` and `pit_02..12` at rim height; `hill_01`, `pit_01` and `pit_04` have no clean skirt). Example: `recolor={"rc_primitives-base": "rock", "rc_primitives-ground": "grass"}` on a hill tile. Every piece also has the author's hand-made UVs, so a material with `mapping=1` (UV) follows them instead of the default box UV. That's useful for a texture that should wrap a sphere or follow a ramp.
- **Ramp facing** follows the built-ins: high side at −z (`ramp_01/05/07/09`, `ramp_round_01/05/10`), high corner at (−x,−z) (`ramp_03/04`, `ramp_round_09`), and `ramp_02` has its ridge along x like `roof`. RC ramps are 0.5 tall, while `wedge` is 1, so use scale y=2 to match it.
- **Most useful pieces for kitbashing:** `barrel_*` (bevelled tanks), `torus` (the built-in torus is Deluxe-only, so this is the usable one), `dome_external`/`dome_doublesided` (caps; double-sided keeps the inside visible), `diamond_gem_*` / `gemstone` / `shard_01/02` (crystals, gems), `container_01..06` (bevelled crates and chunky rocks), `frame_*` (flat rings and frames: rims, hatches, wheel rims stood on edge), `disk_*` / `disk_hole_*` (washers, vents), `step_pyramid_*` / `flat_pyramid_*` (ziggurats, bases), `hill_*` / `pit_*` (terrain tiles; scale x/z for bigger mounds), `ramp_round_*` (skate and quarter-pipe pieces, bowls), `cone_*` / `cylinder_*` in 3–64 sides (the low-sided ones read well for pixel-art sprites).
- **Triangle budget:** default to the light versions: `icosphere_0080` (80) or `sphere_16x08` (224) for spheres, `cylinder_16sided`/`cone_16sided`, `tent_plane_08_*`. The heavy ones are meant as sky domes or hero detail: `icosphere_5120_mirrored_uv` 5,120, `sphere_32x32_doublesided` 3,968, `tent_plane_32_doublesided` 3,844, `torus` 2,048, `sphere_32x32`/`dome_doublesided` 1,984.
- **Built-in equivalents:** `cube`=`block`, `cylinder_32sided`≈`cylinder`, `cylinder_08sided`≈`cylinderVertex`, `cylinder_03sided`≈`blockTriangle` (inscribed, smaller), `cone_32sided`≈`cone`, `cone_04sided`≈`pyramid` (corners on the axes: rot y 45 + scale x/z 1.414 to fill the cell), `icosphere_0080`=`icosphere`, `sphere_*`≈`sphere`, `dome_external`≈`sphere_half`, `dome_quarter_external`≈`sphere_quarter`, `ring_*`≈`cylinderHollow*` (RC rings are thin bands, 0.5 tall), `half_pipe`≈`halfPipe`, `ramp_round_01`≈`halfPipe_half`, `ramp_01`≈`wedge` (y×2), `ramp_02`≈`roof` (y×2), `ramp_03`≈`wedge_cornerOuter` (y×2), `shard_01`≈`diamond`, `cross_01`≈`cross`, `torus`≈`torus%`. A visual check is in `docs/rc-primitives-test/compare_*.png`.
- **Credit** when shipping: "Deluxe Primitives by Reactorcore (reactorcoregames.com), CC-BY 4.0".

## Cars (Vehicles) - `forge/examples/car.py`

Body sections are 1 unit long, y 0.4–1.0. Layout (h = ride drop 0–0.2, w = width 1–1.25, fs = bonnet length 0.75–1):
front `(0,-h,0.5+fs/2)` scale `(w,1,fs)`; body `(0,-h,0)` scale `(w,1,1)`; back `(0,-h,-1)`; roof `body_top*` at `(0,1-h,0)` and `body_topBack*` at `(0,1-h,-1)` (scale y 0.5–1.2 = cabin height); wheels at `(±0.5, 0.3, -0.75)` and `(±0.5, 0.3, 0.4+fs/2)`, left side rot y 180; arches `wheel_cover*` at x ±1; bumpers at `z=0.4+fs/2` and `z=-1` (rot 180). Recolour slot `metalGreen` = paint, `metal` = hood stripe/trim, `metalLight` = chrome.

## Aircraft / arcade ships (Aircraft) - `forge/examples/spaceship.py`

Strict 1-unit grid, pivot bottom-centre, nose toward +z: cockpit/nose at z=+1, `hull_body` at 0, `hull_tail` at −1, `hull_top*` stacked at y=1. `wing_*` are 0.2 thick: place at x=±1, y≈0.3 with `mirror=True`. `wing_long` is 3 units toward −x (pivot at its root's centre, so place at x=−0.5 for the left). Engines scale 0.5–0.6 on the wing tips. Slots: `_defaultMat` = main hull, `metalPurple` = accent, `shield` = canopy. Top-view 48px sprites read very well for shmups.

## Minigolf (Golf) - `forge/examples/minigolf.py`

1-unit tiles. Straights run along +z at rot 0, along +x at rot 90. `bend` at rot 0 turns +z→+x, at rot 180 turns +x→+z. Goal (`end_hole`, `end_roundHole`) gets the direction's rotation +180. Slots: `foliage` = playfield, `bricks` = border, `wood` = props. Decor: `Fences/poles_garlandFlags` at y=0.2 on a straight, `Golf/building_windmill` at y=0.2 over a narrow straight, `Golf/detail_flag` in the hole.

## Buildings (Walls / Roofs / City) - `forge/examples/building.py`

Wall blocks occupy the **−z edge** of the 1x1 cell centred on the pivot (z −0.56..−0.44), 1 unit tall per floor. For a footprint of cells x 0..SX−1, z 0..SZ−1, place walls *in the edge cell* with rotation back(−z)=0, left(−x)=90, front(+z)=180, right(+x)=270. Things that hang *outside* a wall (`cornice_extended`, `City/balcony_basic`) go in the neighbouring outer cell with rotation +180. Quoins (`quoin_*`) sit on the (−x,+z) corner of their cell at rot 0; the corners are (0,SZ−1)@0, (SX−1,SZ−1)@90, (SX−1,0)@180, (0,0)@270. Ground floor: `wall_border`, `doorway_*`, `window_squareGlassLarge`. Roof: `Roofs/roof_flat` on every cell at y=floors. Slots: `stone` = wall, `stoneDark` = plinth/frames, `stoneLight` = trim.

## Mechs / kitbash hybrids (Mech + Zenith_TrackTanks + Aircraft) - `forge/examples/guntank.py`

Mech has no arm piece: build arms as `shoulder_default` (right-handed, mirror for the left) → `socket_medium` rotated (0,0,90) as the upper arm → `socket_medium` rotated (0,90,0) as a forward forearm → `hand_closed` (extends +z from the wrist). Torso stack: `pelvis_belt` → `chest_shoulders` (1 unit tall) → `head_*`. The Zenith tank hull is 0.5 tall, 1 unit per section, and (since the facing fix) faces +z like everything else: `Front 01` at z=+1.0, `Back 01` at z=−1.0, both at rot 0. `Simplified track 01` is a full track loop on the −x side: scale z ≈2.8 for a 3-section hull and mirror it. Name the groups (`turret_upper`, `arm_l`, `cannon_r`, `wings`) so engines can animate them.

## Mass production

Write the build as a function of a few parameters plus a seed (sizes, part choices from lists, palette, texture pick), then loop it to emit variants (`name_01..name_N`). Render one combined review grid rather than reading every sheet, and only inspect outliers in detail.
