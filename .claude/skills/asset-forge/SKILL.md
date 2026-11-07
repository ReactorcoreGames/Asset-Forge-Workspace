---
name: asset-forge
description: Build game-ready 3D models (.glb + Asset Forge .model) and crisp pixel-art sprites from Asset Forge's block library in this workspace. Use for any work order, asset request, prop/vehicle/building/kitbash build, texture-tint choice, sprite render, catalogue lookup, or archiving finished work here.
---

# Asset Forge factory

Asset Forge 2.5.3 has **no CLI and no headless export** (verified by decompiling it: it never reads launch arguments; GLB export only goes through a save dialog; its Lua API can build/load/save/render sprites but cannot export models). So this workspace re-implements what we need in Python on top of the block meshes extracted from the app:

- `forge/forge.py` - `Model` authoring API, `.model` read/write (opens in Asset Forge), assembly, GLB export, renderer, sprites, `deliver()`.
- `Library/` - all blocks extracted by `forge/extract_library.py` (3,234 usable; built-in + custom OBJ collections, including `RC_Primitives`, 167 extra primitives with neutral recolourable slots, see recipes.md).
- `Catalogue/` - `README.md` (collections + part families), `<Collection>.md` (every block: size, min-y, slots), `sheets/*.png` (labelled iso thumbnails).
- `Textures/index.json` - 2,068 tint textures sorted natural/built/abstract; normalised copies installed into Asset Forge as `M32 *` / `S128 *` folders.

Python: always `.venv/Scripts/python` from the workspace root (`pip install -r requirements.txt` to rebuild the venv).

## Work order flow

1. Parse the order: `python forge/workorder.py WorkOrders/<project>.md` (any `.md`/`.txt` that contains an ` ```order ` block works). The format is defined in `WorkOrders/TEMPLATE.md` and written by `WorkOrders/order-form.html`: an ` ```order ` header of `key: value` lines (project, route, engine, facing, surface, texture, palette, glb, sprites, sprite_views, sprite_size, sprite_outline, sprite_same_scale, sprite_rotations, detail, refs, notes), then items as `| # | name | description | qty | ref | notes |` table rows and/or `- item:` snippet blocks. `key=value` pairs in an item's notes override the header for that item. In Python, `load_order(path)` gives each item's effective `settings`; `sprite_specs(settings, ppu)` turns them into `deliver(sprites=...)` dicts. Fix or ask about every WARNING it prints (missing ref images, duplicate names). Only ask about settings the order leaves out; defaults are flat colours, GLB, no sprites, Godot −z, broad strokes. Broad strokes means a convincing silhouette and palette in 1–3 render/fix iterations. Spend more only when the order asks for a hero piece.
   - `facing: +z` → pass `facing="+z"` to `deliver`. `sprite_same_scale: yes` → compute one `fit_ppu(meshes, size, view, rotations=n)` over the whole set and pass it as `ppu` to every sprite. `sprite_rotations: n` → `"rotations": n` in each sprite dict.
   - **Route A (reference images)**: `Read` each `ref_path` image before designing the item. Take from it the silhouette and proportions, the main masses and their arrangement, the palette (pick hex values from it) and the distinctive features (turret, fins, roof shape). Don't chase exact shapes: library blocks can't reproduce curves, faces or organic forms. Characters, animals and organic shapes come out as loose stylisations, so say so in the result. Put the reference next to the preview in the review sheet when you report back.
2. Find parts: `Catalogue/README.md`, then the collection `.md` for sizes/slots, then **look at** `Catalogue/sheets/<Collection>_N.png` before placing anything. `python forge/forge.py find "<regex>" [--collection X]` prints size, min/max (pivot) and material slots.
3. Write `Workbench/<project>/<asset>/build.py` (copy the closest file in `forge/examples/`), run it, then **Read the `*_sheet.png`** (front, iso, right, iso_back, back, top) and fix what's wrong. Never ship unseen geometry.
4. `deliver()` writes `<name>.glb` + `<name>_preview.png` (+ sprites) into `Assets/<project>/`, and `<name>.model` + review sheet into the Workbench folder.
5. After the user collects the assets: `python forge/archive.py <project> --note "..."` moves Workbench + Assets folders into `Archive/` and logs it.

## Large orders (batching)

Any item with qty > 3, or an order of 25+ models (`big_order` in the plan), is mass production. Don't hand-design each model:

1. Group the items into **archetypes**, i.e. models that share a part structure (e.g. "tracked tank", "2-storey house", "crate/barrel prop"). Expect 10–20 archetypes for ~1000 models.
2. Per archetype, write one generator `Workbench/<project>/<archetype>/gen.py` with a function `build(seed, **params) -> Model`. It draws sizes, part choices from curated lists, palette and texture pick from a `random.Random(seed)`. Get the first instance right with the normal sheet review.
3. Render the variants as 5×5 grids: `review_grid([(name, model), ...], path)` (25 per sheet). `Read` each grid and fix the generator's ranges or lists when outliers appear (floating parts, clipping, ugly palettes). Inspect single sheets only for outliers. Show the user the first grid per archetype before running the whole batch.
4. Emit the variants with `deliver(...)` as `name_01..name_N`, then one `_overview.png` grid per archetype in `Assets/<project>/`.
5. Keep `Workbench/<project>/PROGRESS.md` updated: archetypes done or pending, generator paths, seeds used, open issues. A session that runs low stops at an archetype boundary, and the next fresh session continues from PROGRESS.md.

Rough budget on Claude Pro: a hand-built unique model costs 10–20k tokens and a generator 20–40k, while variants are nearly free.

## Authoring API (cheat sheet)

```python
ROOT = next(p for p in Path(__file__).resolve().parents if (p / "forge" / "forge.py").exists())
sys.path.insert(0, str(ROOT / "forge"))
from forge import Model, deliver, find, block_info
m = Model()
m.mat("paint", "#D7263D", metallic=0.3, gloss=0.6)              # flat colour
m.mat("turf", "#5BC24A", texture="M32 Natural/m32_nat_597.png")  # tinted texture (scale=1 -> 1 tile per unit)
m.add("Vehicles/body_sports", pos, rot=(0, 90, 0), scale=(1.15, 1, 1),
      recolor={"metalGreen": "paint"},   # map the block's slot materials to yours
      group="body",                      # becomes a GLB node (name groups you'll animate)
      mirror=True)                       # also place an X-mirrored copy
deliver(m, "sports_car", here, ROOT / "Assets" / project,
        sprites=[{"view": "right", "size": 64, "upscale_preview": 6}])
```

- Coordinates are **Asset Forge (Unity) space**: +Y up, **front = +Z**, +X = model's right. 1 unit ≈ one block cell. Rotations are Unity euler degrees (applied Z, then X, then Y).
- Slot materials: each block has ordered slots (`block_info(key)["slots"]`). Unmapped slots keep Asset Forge's default colours. A material name is global within a model, so two parts that need different colours of the same slot need different material names.
- Custom-collection slots are prefixed with the lowercased collection, e.g. `zenith_tracktanks-blueSteel`. RC_Primitives uses `rc_primitives-base` / `-inner` / `-ground`.
- The renderer draws both sides of every triangle but lets back faces lose depth ties, so coincident double-sided shells preview like the engine's back-face culling.
- `mirror=True` uses scale.x = -1 (Asset Forge handles negative scale), so asymmetric parts mirror correctly.
- Deluxe-only blocks (`%` in the name, 129 of them) are hidden: the user owns the standard edition, so those blocks would vanish when the `.model` is opened in the app. `find(..., deluxe=True)` only if the user asks.

## Output conventions

- The user's engines are **Godot** (primary) and possibly **three.js**. GLB matches Asset Forge's own exporter (UniGLTF ReverseZ): **+Y up, model front faces −Z** (Godot forward), 1 unit = 1 m. For three.js (where `Object3D.lookAt` aims +Z) pass `facing="+z"` to `deliver`/`export_glb` (CLI `--facing +z`) if the work order asks for it. `center="base"` (default in `deliver`) puts the footprint centre at the origin on y=0.
- One node per group (ungrouped → `body`), primitives per material. Base colours are converted sRGB→linear. Textures are embedded with nearest filtering and repeat wrap.
- Textured materials get Asset Forge's world-space box UVs (`UVMapping.BoxUV`), so tiling density is uniform across parts. `scale` on the material multiplies tiling (0.5 = texture spans 2 units).
- Review the triangle count printed by `deliver` (a 4x3x3 building ≈ 13k tris). For mass props prefer fewer, bigger blocks, and the light RC_Primitives (`icosphere_0080`, `sphere_16x08`, 8–16-sided cylinders and cones). The 2–5k-tri spheres, domes and tent planes are for sky domes or a hero piece the order asks for.

## Textures

- Modes: **flat** (no texture), **m32** = 32px Microart (pixel-art/N64 crunch), **s128** = 128px SurfaceTex (PS1/lowpoly). Categories: `natural` (rock, dirt, grass, bark, raw wood grain, water, grunge), `built` (bricks, cobble walls, tiles, planks, grids, plates, stripes), `abstract` (lace/fabric motifs, mandalas, checkers, gradients, camo, bokeh).
- Random pick (the user's "slap a random texture on it" flow): `from textures import pick; pick("micro32", "natural", seed)` returns an AF ref like `M32 Natural/m32_nat_412.png`. Browse visually via `Textures/sheets/<pack>_<category>_N.png`.
- Always use the normalised `M32 */S128 *` refs: brightness is shifted to mean 0.62 and contrast clamped to std 0.07–0.17, so any tint stays recognisable. The raw SurfaceTex files sit in a nested folder that Asset Forge cannot see.
- Tint = material colour × texture, so pick the tint as the colour you want the mid-tones to be.

## Sprites (2D)

`sprite(mesh, path, size, view, bands=3, outline="dark", colors=0, ppu=None)`: orthographic, no anti-aliasing, hard alpha, cel-banded light (material colours stay pure), 1px darkened outline. Views: `front back left right top bottom iso iso_left iso_back dimetric trueiso high` or `"yaw,pitch"` (yaw 0 = front, 90 = right; `right` = side-scroller facing right; `top` = front points up the screen). For a consistent sprite *set*, pass the same `ppu` (pixels per unit) to every asset instead of auto-fit (`fit_ppu` computes one that fits them all). Rotation sets: add `"rotations": 8` to a `deliver` sprite dict to get `_r000`, `_r045` … files, each with the model turned about +Y. `colors=N` adds a median-cut palette limit (useful with textures). Any canvas size works (tested 16–1024px, each under 1 s); 32–128px is the pixel-art sweet spot. Save `upscale_preview` copies in the Workbench for review only.

## CLI helpers

```
forge/forge.py find "^Aircraft/wing" | info Mech/hand_closed
forge/forge.py export|render|sheet|sprite <file.model> <out> [--view --size --bands --outline --ppu]
forge/catalogue.py [Collection]          # rebuild catalogue (after adding collections)
forge/extract_library.py [--custom-only] # re-extract blocks (after adding collections/updating AF)
forge/rotate_collection.py <Collection> [--only stems...] [--dry-run]  # turn -z-authored OBJs to +z (backs up first)
forge/import_collection.py <src_dir> --config forge/packs/<pack>.json [--dry-run] [--force]  # standardise a raw OBJ pack into Collections/
forge/textures.py classify|sheets [--ordered]|normalize|install|pick <pack> <cat>
forge/archive.py <project> --note "..."
forge/workorder.py WorkOrders/<project>.md [--json]   # parse + check a work order
```

Python helpers beyond the cheat sheet: `review_grid(items, path)` (batch thumbnails), `fit_ppu(meshes, size, view, rotations=1)` (shared sprite scale), `rotate_y(mesh, deg)`.

Placement recipes per category (cars, aircraft grid, golf connections, building wall rotations, mech arms, kitbashing across collections) are in [recipes.md](recipes.md). Read it before building in a category for the first time.
