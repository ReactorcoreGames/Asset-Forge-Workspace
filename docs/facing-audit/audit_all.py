"""Render every block of one collection in a given view, labelled with z range."""
import sys
from pathlib import Path
sys.path.insert(0, r"C:/ClaudeWorkspace/Asset-Forge-Workspace/forge")
import forge
from PIL import Image, ImageDraw
col, view, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
pat = sys.argv[4] if len(sys.argv) > 4 else "."
lib = forge.library()["blocks"]
keys = forge.find(pat, col)
T, cols = 150, 6
rows = (len(keys) + cols - 1) // cols
sheet = Image.new("RGB", (cols * T, rows * (T + 14)), (24, 25, 29))
d = ImageDraw.Draw(sheet)
for i, k in enumerate(keys):
    m = forge.Model(); m.add(k)
    im = forge.render(m.assemble(), None, T, view, bg="#34363D")
    x, y = (i % cols) * T, (i // cols) * (T + 14)
    sheet.paste(im, (x, y))
    b = lib[k]
    d.text((x + 2, y + T), k.split("/", 1)[1][-24:], fill=(230, 230, 230))
    d.text((x + 2, y + 2), f"z {b['min'][2]:.2f}..{b['max'][2]:.2f}", fill=(255, 200, 80))
sheet.save(out)
