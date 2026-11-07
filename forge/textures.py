"""Sort, index and normalise the greyscale tint texture packs.

Packs (originals are never modified):
  micro32 - Textures/32px Microart/tex_Micro*.png        (32x32)
  surf128 - Textures/128px SurfaceTex/Textures/*.png     (128x128)

Commands
  classify   compute features + heuristic natural/built/abstract labels -> Textures/index.json
             (manual overrides in Textures/overrides.json win over the heuristic)
  sheets     numbered contact sheets per pack+category -> Textures/sheets/
  normalize  brightness/contrast-normalised copies -> Textures/normalized/<pack>/<category>/
  install    copy the normalised sorted sets into Asset Forge's Textures folder so the app's
             texture browser shows them (folders 'M32 Natural', 'S128 Built', ...)
  pick       print a random texture ref:  pick micro32 natural [--seed N] [--raw]
"""
import json
import random
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
AF_TEX = ROOT / "Asset Forge 2.5.3 (Windows)" / "Textures"
OUT = ROOT / "Textures"
PACKS = {
    "micro32": (AF_TEX / "32px Microart", "tex_Micro*.png", "M32"),
    "surf128": (AF_TEX / "128px SurfaceTex" / "Textures", "*.png", "S128"),
}
CATS = ("natural", "built", "abstract")
# target stats for normalised copies (greyscale 0..1); multiply-tint stays readable around here
TARGET_MEAN, MIN_STD, MAX_STD = 0.62, 0.07, 0.17


def load_gray(path):
    return np.asarray(Image.open(path).convert("L"), np.float64) / 255


def features(g):
    n = g.shape[0]
    z = g - g.mean()
    var = (z ** 2).sum() + 1e-9
    F = np.fft.fft2(z)
    # periodicity: strongest circular autocorrelation peak away from the origin
    ac = np.real(np.fft.ifft2(F * np.conj(F))) / var
    yy, xx = np.meshgrid(np.fft.fftfreq(n) * n, np.fft.fftfreq(n) * n, indexing="ij")
    r = np.hypot(yy, xx)
    period = float(ac[r >= max(3, n / 8)].max())
    # mirror symmetry under any circular shift (ornamental / designed patterns)
    sym = 0.0
    for flipped in (g[:, ::-1], g[::-1, :]):
        zf = flipped - flipped.mean()
        cc = np.real(np.fft.ifft2(F * np.conj(np.fft.fft2(zf)))) / var
        sym = max(sym, float(cc.max()))
    # Orientation coherence from a smoothed structure tensor. Raw pixel gradients would call
    # single-pixel noise "axis aligned", so the tensor is averaged over a window ~n/12 wide.
    gx = (np.roll(g, -1, 1) - np.roll(g, 1, 1)) / 2
    gy = (np.roll(g, -1, 0) - np.roll(g, 1, 0)) / 2
    sigma = max(1.5, n / 12)
    kern = np.exp(-0.5 * (r / sigma) ** 2)
    K = np.fft.fft2(kern / kern.sum())
    smooth = lambda a: np.real(np.fft.ifft2(np.fft.fft2(a) * K))
    jxx, jyy, jxy = smooth(gx * gx), smooth(gy * gy), smooth(gx * gy)
    tr = jxx + jyy + 1e-12
    coh_map = np.sqrt((jxx - jyy) ** 2 + 4 * jxy ** 2) / tr
    coherence = float((coh_map * tr).sum() / tr.sum())
    theta = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) % 180
    near = (np.minimum(theta, 180 - theta) < 12) | (np.abs(theta - 90) < 12)
    axis = float((coh_map * tr * near).sum() / ((coh_map * tr).sum() + 1e-12))
    # posterisation: share of pixels in the 4 most common of 32 grey bins
    hist = np.bincount(np.clip((g * 32).astype(int), 0, 31).ravel(), minlength=32)
    flat = float(np.sort(hist)[-4:].sum() / hist.sum())
    return {"period": round(period, 3), "sym": round(sym, 3), "axis": round(axis, 3),
            "coh": round(coherence, 3),
            "flat": round(flat, 3), "mean": round(float(g.mean()), 3), "std": round(float(g.std()), 3)}


def heuristic(f):
    """First-pass guess; a visual review pass corrects it via overrides.json."""
    if f["period"] < 0.5 and f["sym"] < 0.6:
        return "natural"            # irregular, non-repeating
    if f["axis"] > 0.5:
        return "built"              # coherent straight horizontal/vertical structure
    if f["sym"] > 0.75 and f["period"] > 0.6:
        return "abstract"           # mirrored, repeating motifs
    if f["period"] > 0.85:
        return "built"
    return "natural"


def classify():
    OUT.mkdir(exist_ok=True)
    ov_path = OUT / "overrides.json"
    overrides = json.loads(ov_path.read_text()) if ov_path.exists() else {}
    index = []
    for pack, (folder, pattern, _) in PACKS.items():
        files = sorted(folder.glob(pattern), key=lambda p: (len(p.stem), p.stem))
        for i, p in enumerate(files):
            f = features(load_gray(p))
            key = f"{pack}/{p.name}"
            cat = overrides.get(key) or heuristic(f)
            index.append({"id": f"{pack}:{i}", "pack": pack, "file": p.name,
                          "src": p.relative_to(AF_TEX).as_posix(), "category": cat,
                          "auto": heuristic(f), **f})
    (OUT / "index.json").write_text(json.dumps(index, indent=0))
    for pack in PACKS:
        counts = {c: sum(1 for t in index if t["pack"] == pack and t["category"] == c) for c in CATS}
        print(pack, counts)
    return index


def load_index():
    return json.loads((OUT / "index.json").read_text())


def sheets(cols=16, tile=64, ordered=False):
    """Contact sheets per pack+category, or (ordered=True) whole packs in id order."""
    font = ImageFont.load_default()
    index = load_index()
    sdir = OUT / "sheets"
    sdir.mkdir(parents=True, exist_ok=True)
    for pack in PACKS:
        for cat in (("all",) if ordered else CATS):
            items = [t for t in index if t["pack"] == pack and (ordered or t["category"] == cat)]
            per = cols * 10
            for s in range(0, len(items), per):
                chunk = items[s:s + per]
                rows = (len(chunk) + cols - 1) // cols
                sheet = Image.new("RGB", (cols * tile, rows * (tile + 11)), (20, 20, 24))
                d = ImageDraw.Draw(sheet)
                for i, t in enumerate(chunk):
                    im = Image.open(AF_TEX / t["src"]).convert("RGB").resize((tile, tile), Image.NEAREST)
                    x, y = (i % cols) * tile, (i // cols) * (tile + 11)
                    sheet.paste(im, (x, y))
                    d.text((x + 2, y + tile), t["id"].split(":")[1], fill=(230, 230, 120), font=font)
                sheet.save(sdir / f"{pack}_{cat}_{s // per + 1}.png")


def normalize_img(g):
    """Shift mean to TARGET_MEAN, clamp contrast into [MIN_STD, MAX_STD]. Keeps relative detail."""
    m, s = g.mean(), g.std()
    target_s = min(max(s, MIN_STD), MAX_STD)
    gain = target_s / s if s > 1e-4 else 1.0
    out = (g - m) * gain + TARGET_MEAN
    return np.clip(out, 0, 1)


def normalize():
    index = load_index()
    base = OUT / "normalized"
    for t in index:
        g = load_gray(AF_TEX / t["src"])
        dst = base / t["pack"] / t["category"] / t["file"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray((normalize_img(g) * 255).round().astype(np.uint8), "L").convert("RGB").save(dst)
    print(f"wrote {len(index)} normalised textures to {base}")


def install():
    """Expose sorted sets to Asset Forge: Textures/<'M32 Natural' ...>/*.png (normalised copies)."""
    index = load_index()
    for pack, (_, _, short) in PACKS.items():
        for cat in CATS:
            d = AF_TEX / f"{short} {cat.capitalize()}"
            d.mkdir(exist_ok=True)  # files are overwritten in place, nothing is deleted
            for t in index:
                if t["pack"] == pack and t["category"] == cat:
                    src = OUT / "normalized" / pack / cat / t["file"]
                    name = f"{short.lower()}_{cat[:3]}_{t['id'].split(':')[1]}.png"
                    shutil.copyfile(src, d / name)
    print("installed into", AF_TEX)


def af_ref(t, normalized=True):
    """Asset Forge texture reference for an index entry."""
    if not normalized:
        return t["src"] if t["pack"] == "micro32" else None  # SurfaceTex originals are nested; AF can't see them
    short = PACKS[t["pack"]][2]
    return f"{short} {t['category'].capitalize()}/{short.lower()}_{t['category'][:3]}_{t['id'].split(':')[1]}.png"


def pick(pack, cat, seed=None, normalized=True):
    rng = random.Random(seed)
    items = [t for t in load_index() if t["pack"] == pack and t["category"] == cat]
    return af_ref(rng.choice(items), normalized)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "classify"
    if cmd == "classify":
        classify()
    elif cmd == "sheets":
        sheets(ordered="--ordered" in sys.argv)
    elif cmd == "normalize":
        normalize()
    elif cmd == "install":
        install()
    elif cmd == "pick":
        seed = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else None
        print(pick(sys.argv[2], sys.argv[3], seed, "--raw" not in sys.argv))


if __name__ == "__main__":
    main()
