import sys
from pathlib import Path
sys.path.insert(0, r"C:/ClaudeWorkspace/Asset-Forge-Workspace/forge")
import forge
from PIL import Image, ImageDraw
out = Path(sys.argv[1]); keys = sys.argv[2:]
views = ["front", "back", "right", "top"]
T = 150
sheet = Image.new("RGB", (len(views) * T, len(keys) * (T + 14)), (24, 25, 29))
d = ImageDraw.Draw(sheet)
for r, k in enumerate(keys):
    m = forge.Model(); m.add(k); mesh = m.assemble()
    for c, v in enumerate(views):
        sheet.paste(forge.render(mesh, None, T, v, bg="#34363D"), (c * T, r * (T + 14)))
        d.text((c * T + 2, r * (T + 14) + T), f"{k.split('/')[-1][-16:]} {v}", fill=(230, 230, 230))
sheet.save(out)
