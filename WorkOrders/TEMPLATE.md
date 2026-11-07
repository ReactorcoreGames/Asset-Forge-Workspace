# Work order: <project-name>

The easiest way to fill this in is `WorkOrders/order-form.html` (open it in a browser). It remembers your previous choices and writes this exact format for you. To write an order by hand, copy this file to `WorkOrders/<project-name>.md` and edit the block and the table. A line you leave out falls back to the default shown in the comments below.

Both routes use the same format:

- **Route A (reference images):** every item has a `ref` image. Put the images in `WorkOrders/<project-name>/refs/` and use the bare filename in the `ref` column.
- **Route B (written list):** describe items in words. You can keep the list in any `.md` or `.txt` file, as long as it contains the `order` block. Items can be table rows or `- item:` snippet blocks (the form generates these), mixed freely.

```order
project: my-project          # folder-safe name: Assets/<project>/, Workbench/<project>/
route: B                     # A = reference image per item, B = written list
engine: godot                # godot | threejs | other
facing: -z                   # -z (Godot / glTF default) | +z (three.js lookAt)
surface: flat                # flat | m32 (32px Microart + tint) | s128 (128px SurfaceTex + tint)
texture: none                # natural | built | abstract | random (ignored when surface is flat)
palette: free choice         # a vibe and/or hex codes, e.g. desert military | #C2A878 #5A5F3C
glb: yes                     # yes | no
sprites: no                  # yes | no; the sprite_* lines only matter when this is yes
sprite_views: right          # comma list: right left front back top iso iso_left iso_back dimetric trueiso high
sprite_size: 64              # any canvas size in px; 32-128 is the pixel-art sweet spot
sprite_outline: dark         # dark | black | none
sprite_same_scale: yes       # yes = one pixels-per-unit across the whole set
sprite_rotations: 1          # 1 | 4 | 8 | 16 turns of the model per view
detail: broad                # broad (mass-producible) | hero
refs: WorkOrders/my-project/refs/
notes:                       # anything that applies to every item
```

## Items

| # | name | description | qty | ref | notes |
|---|---|---|---|---|---|
| 1 | scout_buggy | two-seat desert buggy with roll cage and big rear wheels | 6 | scout_buggy.jpg | animate wheels; surface=flat |

The same item written as a snippet block (Route B lists):

```
- item: scout_buggy
  desc: two-seat desert buggy with roll cage and big rear wheels
  qty: 6
  ref: scout_buggy.jpg
  notes: animate wheels; surface=flat
```

Column meanings:

- **name**: file name for the asset (lowercase, underscores). Variants become `name_01`, `name_02`, and so on.
- **description**: what it is, plus the must-have features.
- **qty**: how many distinct variants to make. `1` = one model.
- **ref**: optional reference image filename (required on Route A). It guides silhouette, palette and vibe, not exact shapes.
- **notes**: sizes, parts that must be present, groups to animate (e.g. `turret`, `wheels`), and per-item overrides of any header line written as `key=value` and separated by `;` (e.g. `surface=s128; texture=natural; sprite_size=32`).

Check an order before sending it: `.venv/Scripts/python forge/workorder.py WorkOrders/<project-name>.md`
