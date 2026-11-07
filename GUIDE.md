# Asset Forge factory: user guide

A plain-language manual for coming back to this workspace after a long break. For the technical details Claude uses, see `.claude/skills/asset-forge/SKILL.md` and `recipes.md`.

## What this is

This folder is a small factory for game assets. You describe what you want in a work order, Claude assembles 3D models out of the Asset Forge block library (Kenney's built-in blocks plus the custom collections you added), and you collect the finished files: `.glb` models for your engine and, if you ask for them, pixel-art sprites.

Asset Forge itself has no command line, so Claude doesn't drive the app. Instead, a Python toolchain in `forge/` reads the same blocks, writes `.model` files that open in Asset Forge, exports GLB with the same axis conventions as Asset Forge's own exporter, and renders previews and sprites. You can open any `.model` in Asset Forge to tweak it by hand.

## Folder map

| folder | what's in it | who touches it |
|---|---|---|
| `Asset Forge 2.5.3 (Windows)/` | the app, its Collections (custom block packs), Textures, Samples | you. Claude only adds sorted texture folders (`M32 *`, `S128 *`) and, once with your approval, standardised the facing of some collections (see below) |
| `WorkOrders/` | your orders (`<project>.md`), the order form (`order-form.html`), the template (`TEMPLATE.md`), reference images (`<project>/refs/`) | you (Claude may draft) |
| `Assets/<project>/` | finished deliverables: `.glb`, preview PNG, sprites | Claude writes, you collect |
| `Workbench/<project>/` | work in progress: build scripts, `.model` files, review sheets | Claude |
| `Archive/` | finished projects moved out of the way, plus `LOG.md` listing them | `forge/archive.py` |
| `forge/` | the Python toolchain and example build scripts | Claude |
| `Library/` | block meshes extracted from Asset Forge (can be rebuilt; keep private) | generated |
| `Catalogue/` | an index of every block with contact sheets, for finding parts | generated |
| `Textures/` | texture index, normalised copies, review sheets | generated |
| `GUIDE.md` | this file | |

Generated folders (`Library/`, `Catalogue/`, `Textures/`) can always be rebuilt from the scripts, so it's fine if they get stale or deleted.

## Placing a work order

There are two routes, and both use the same order format.

- **Route A, reference images:** one picture per item. Put the images in `WorkOrders/<project>/refs/` and give each item its image's filename. Good when you have concept art, screenshots or sketches.
- **Route B, written list:** describe each item in words, optionally with a reference image. Good for long lists of props, buildings and variants.

The easiest way to write either kind is the form:

1. Open `WorkOrders/order-form.html` in your browser (double-click it; no server is needed).
2. Set the global defaults: project name, engine, surface mode, palette, GLB and sprite settings, detail level. The form remembers these in your browser, so next time you only change what's different.
3. Add items: name, description, quantity (number of variants), reference image filename, notes. On Route A you can paste a list of image filenames and the form creates one item per image.
4. Copy **1. Order file** into `WorkOrders/<project>.md` (or use Download .md and move the file there).
5. Copy **3. Prompt for Claude** and paste it into a Claude Code session in this workspace.

If you already keep a running list in a `.md` or `.txt` file, paste the form's `order` header block into it once, then paste the **2. Item snippets** blocks under it as you add things. Table rows and snippet blocks can be mixed in one file.

You can also skip the form: copy `WorkOrders/TEMPLATE.md`, which documents every field. In an item's notes, `key=value` overrides a global setting for that item only, e.g. `surface=flat; sprite_size=32`. To check an order before sending it, run `.venv/Scripts/python forge/workorder.py WorkOrders/<project>.md`. It lists what it understood and warns about missing images or duplicate names.

Anything you leave out falls back to: flat colours, GLB on, no sprites, Godot facing, broad-strokes detail.

## What you get back, and where

Everything you collect lands in `Assets/<project>/`:

- `<name>.glb`: the model. +Y up, 1 unit = 1 metre, origin at the centre of its footprint on the ground. Named groups (e.g. `turret`, `wheels`, `arm_l`) become separate nodes you can animate.
- `<name>_preview.png`: a 512px isometric preview.
- `<name>_sprite_<view>_<size>.png`: sprites, if you ordered them. Rotation sets add `_r000`, `_r045` and so on.
- For big orders, an `_overview.png` grid per archetype.

The matching `.model` file (opens in Asset Forge) and a six-view review sheet stay in `Workbench/<project>/<asset>/`, along with the build script that made it. Any asset can be regenerated or tweaked later from there.

## Collecting and archiving

Copy or move what you want from `Assets/<project>/` into your game project. When you're done with a project, tell Claude to archive it, or run:

`.venv/Scripts/python forge/archive.py <project> --note "what was built"`

This moves `Workbench/<project>` and whatever is left in `Assets/<project>` into `Archive/<date>_<project>/`, copies the work order alongside, and adds a line to `Archive/LOG.md`. Nothing is deleted, so an archived build can be reopened and rebuilt.

## Surface modes and texture categories

Three ways to surface a model:

- **flat**: plain colours per material. Cleanest and best for sprites and toy-like styles.
- **m32**: the 32px Microart greyscale textures, tinted by the material colour. Gives a crunchy N64/pixel-art look.
- **s128**: the 128px SurfaceTex greyscale textures, tinted. Reads as PS1/lowpoly with more surface detail.

Textured modes pick from three categories:

- **natural**: rock, dirt, grass, bark, raw wood grain, water, grunge.
- **built**: bricks, cobble walls, tiles, planks, grids, metal plates, stripes.
- **abstract**: lace and fabric motifs, mandalas, checkers, gradients, camo, bokeh.
- **random**: Claude picks across the categories.

Tint works as colour × texture, so the colour you name is roughly what the mid-tones will look like. The textures were brightness-normalised so that any tint stays recognisable. You can browse them as numbered sheets in `Textures/sheets/`, or in Asset Forge's texture browser under the `M32 …` and `S128 …` folders, and name a specific one in an order if you like.

## Sprite options

Sprites are rendered straight from the 3D model: no anti-aliasing, hard edges, cel-banded lighting that keeps material colours pure, and an optional 1px outline.

- **Views:** `right` (side-scroller facing right), `left`, `front`, `back`, `top` (front points up the screen, for top-down shooters), `iso`, `iso_left`, `iso_back`, `dimetric` (2:1 pixel-art isometric), `trueiso`, `high` (a steep three-quarter view).
- **Size:** any canvas size works (tested from 16 to 1024px). 32–128px is the pixel-art sweet spot.
- **Outline:** `dark` (a darkened version of the edge colour), `black`, or `none`.
- **Consistent scale:** `yes` renders the whole set at the same pixels per unit, so a truck stays bigger than a car. `no` makes every sprite fill its canvas.
- **Rotations:** 1, 4, 8 or 16 turns of the model per view, for directional sprites (e.g. 8-way top-down units).

## Godot vs three.js facing

Every model is built facing +Z inside Asset Forge. The GLB export then flips it to match the engine:

- **Godot (default, `facing: -z`):** the model's front faces −Z, Godot's forward direction. This also matches Asset Forge's own GLB export.
- **three.js (`facing: +z`):** the front faces +Z, which is what `Object3D.lookAt` expects. Choose three.js in the form, or put `facing: +z` in the order.

For other engines, pick "Other" in the form and choose the facing that engine treats as forward.

On 2026-10-24 the custom collections were standardised so that every block faces +Z like the built-in ones. Mixing collections no longer needs 180° corrections. The details are in `recipes.md` and `docs/facing-audit/AUDIT.md`.

## Adding new collections or textures

**A new block collection:** drop the OBJ folder (with its `.mtl` files) into `Asset Forge 2.5.3 (Windows)/Collections/`, check that it appears in the app, then ask Claude to "add the new collection". Claude runs `forge/extract_library.py --custom-only` and `forge/catalogue.py`, and checks the new collection's facing. If it faces −Z, Claude backs up the originals and rotates it so it matches the rest. The same applies after updating Asset Forge: re-extract (without `--custom-only` if the built-in blocks changed).

**A raw model pack that isn't made for Asset Forge** (different scale, centred pivots, no `.mtl`, like your Deluxe Primitives): don't drop it into Collections. Put it anywhere in the workspace and ask Claude to add it as a new collection. Claude studies it, shows you a standardisation plan (scale, pivots, facing, material slots, names) and, once you approve, writes a small config in `forge/packs/` and runs `forge/import_collection.py`. That script writes standardised copies into `Collections/<Name>/` and never changes your originals, so a collection can always be rebuilt from its pack and config. Your Deluxe Primitives went in this way as `RC_Primitives`: 167 grey primitives at the same scale as Asset Forge's own Primitives, with three recolourable slots (base, inner, ground).

**New textures:** greyscale PNGs dropped into `Asset Forge 2.5.3 (Windows)/Textures/<folder>/` show up in the app straight away. To get them sorted into natural/built/abstract and usable in work orders, ask Claude to add the pack to `forge/textures.py`. Claude then runs `classify`, `normalize`, `install` and `sheets`. Wrong category guesses can be corrected in `Textures/overrides.json`.

## Keep Asset Forge installed

Asset Forge is still needed even though Claude doesn't drive it:

- it is the source of the block library (`Library/` is extracted from it),
- it is the best viewer for checking a `.model` in 3D,
- it is the editor for hand tweaks to anything Claude builds.

The extraction uses UnityPy, which is just a Python library for reading Unity data files, so Unity itself is not needed.

## Licensing

- Asset Forge blocks are CC0, and models you build with them can be used commercially.
- The Asset Forge app itself must not be shared. `Library/` holds meshes extracted from the app, so keep it private: never publish it or put it in a public repo. The repo's `.gitignore` keeps the app, `Library/`, `Catalogue/`, third-party collections and your work folders (`Workbench/`, `Assets/`, `Archive/`, `old wip/`) out of git. Only your own packs inside the Asset Forge folder (`Collections/RC_Primitives`, `Textures/32px Microart`, `Textures/128px SurfaceTex`) are committed.
- The Microart and SurfaceTex texture packs are your own (CC-BY 4.0).
- The `RC_Primitives` collection is your Deluxe Primitives pack (CC-BY 4.0). Credit "Reactorcore, reactorcoregames.com" as usual.
- Third-party custom collections carry their authors' licences. Check each one before shipping a game that uses them.

## Cost expectations (Claude Pro)

What things cost, in rough terms:

- **Hand-built unique models** cost roughly 10–20k new tokens each: parts lookup, the build script, and one to three look-and-fix rounds. That's about 15–30 models per session.
- **Mass production** should use a parametric generator per archetype ("tracked tank", "suburban house", "crate/barrel prop"). A generator costs 20–40k tokens once. After that, variants are nearly free, and Claude reviews them as 25-thumbnail grids instead of one by one.
- **1,000 models is realistic** as variants of 10–20 archetypes spread over a few sessions. It is not realistic as 1,000 hand-designed models.
- **Split big orders across fresh sessions.** Claude keeps `Workbench/<project>/PROGRESS.md` up to date so the next session picks up where the last stopped. A fresh session is cheaper than a very long one.
- **Model choice:** use Opus to design the archetypes and generators. Sonnet is likely fine for routine variant runs from existing generators.
- **Compared with a Blender MCP workflow**, this is much cheaper and fully repeatable (same script, same result), but you are limited to what the block library can make.

## What reference images can and can't do

Reference images capture the **silhouette, proportions, palette and overall vibe**, not exact shapes. Claude studies the picture and rebuilds it from blocks, so expect a recognisable kitbash interpretation, not a replica.

- **Works well:** vehicles, buildings, props, mechs, spaceships, weapons. These are blocky, made of parts, and well covered by the library.
- **Works poorly:** characters, animals and other organic shapes (faces, muscles, fur, curves). These come out as loose, toy-like stylisations at best.

One clear image per item works best: side or three-quarter view, plain background, the whole object in frame.
