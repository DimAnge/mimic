#!/usr/bin/env python3
"""Prepare device photos for the README and the site.

Resizes, gently lifts the shadows so the printed texture reads, and cuts a
landscape hero crop. Source photos stay untouched.

    python3 tools/make_photos.py /path/to/uploads
"""
import os
import sys

from PIL import Image, ImageEnhance, ImageOps

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "docs", "assets", "photos")
os.makedirs(OUT, exist_ok=True)

SRC = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads"

# source file -> (output name, long edge, crop box as fractions or None)
JOBS = [
    ("1000015637.jpg", "desk", 1600, None),
    ("1000015641.jpg", "games", 1400, (0.10, 0.22, 0.95, 0.72)),
    ("1000015638.jpg", "stand", 1600, None),
    ("1000015640.jpg", "usage", 1400, (0.14, 0.26, 0.92, 0.70)),
    ("1000015639.jpg", "weather-desk", 1600, None),
    ("1000015642.jpg", "weather", 1400, (0.14, 0.26, 0.92, 0.70)),
]


def prepare(img, long_edge, crop=None):
    img = ImageOps.exif_transpose(img).convert("RGB")
    if crop:
        w, h = img.size
        img = img.crop((int(crop[0] * w), int(crop[1] * h),
                        int(crop[2] * w), int(crop[3] * h)))
    w, h = img.size
    scale = long_edge / max(w, h)
    if scale < 1:
        img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    img = ImageEnhance.Brightness(img).enhance(1.06)
    img = ImageEnhance.Contrast(img).enhance(1.06)
    img = ImageEnhance.Sharpness(img).enhance(1.25)
    return img


for src, name, edge, crop in JOBS:
    path = os.path.join(SRC, src)
    if not os.path.exists(path):
        print("skip (missing):", src)
        continue
    out = prepare(Image.open(path), edge, crop)
    dst = os.path.join(OUT, name + ".jpg")
    out.save(dst, "JPEG", quality=84, optimize=True, progressive=True)
    print("wrote", os.path.relpath(dst, HERE), out.size,
          "%.0f KB" % (os.path.getsize(dst) / 1024))

# landscape hero for the top of the README and the site
hero_src = os.path.join(SRC, "1000015638.jpg")
if os.path.exists(hero_src):
    img = ImageOps.exif_transpose(Image.open(hero_src)).convert("RGB")
    w, h = img.size
    box = (0, int(0.27 * h), w, int(0.85 * h))
    hero = prepare(img.crop(box), 1600)
    dst = os.path.join(OUT, "hero.jpg")
    hero.save(dst, "JPEG", quality=85, optimize=True, progressive=True)
    print("wrote", os.path.relpath(dst, HERE), hero.size,
          "%.0f KB" % (os.path.getsize(dst) / 1024))


# ---------------------------------------------------------------------------
# Recover screen panels from close-up photos, for the screens that would not
# capture cleanly over serial. Finds the glass, squares it up, and thresholds
# it back to two colours so it sits beside the real dumps.
# ---------------------------------------------------------------------------
import numpy as np
from PIL import ImageDraw

GLOW = (191, 227, 255)
SCREEN = (8, 10, 12)
CASE = (22, 24, 26)
PAPER = (231, 233, 230)


def find_glass(arr):
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    cyan = (b > r + 35) & (b > 110)
    ys, xs = np.where(cyan)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    red = (r > g + 45) & (r > 90)

    def walk(axis, start, step, limit):
        pos = start
        while 0 <= pos + step < limit:
            pos += step
            strip = red[pos, x0:x1] if axis == "y" else red[y0:y1, pos]
            if strip.mean() > 0.30:
                break
        return pos

    return (walk("x", x0, -1, arr.shape[1]), walk("y", y0, -1, arr.shape[0]),
            walk("x", x1, 1, arr.shape[1]), walk("y", y1, 1, arr.shape[0]))


def otsu(gray):
    hist, _ = np.histogram(gray, bins=256, range=(0, 256))
    total = gray.size
    sum_all = np.dot(np.arange(256), hist)
    best, thresh, w_b, sum_b = -1.0, 128, 0.0, 0.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        var = w_b * w_f * ((sum_b / w_b) - ((sum_all - sum_b) / w_f)) ** 2
        if var > best:
            best, thresh = var, t
    return thresh


def panel_from_photo(src, dst, scale=4, trim=2):
    img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    arr = np.asarray(img).astype(int)
    x0, y0, x1, y1 = find_glass(arr)
    crop = img.crop((x0 + trim, y0 + trim, x1 - trim, y1 - trim))
    crop = crop.resize((128 * scale, 64 * scale), Image.LANCZOS)

    gray = np.asarray(crop.convert("L")).astype(float)
    gray = (gray - gray.min()) / max(gray.max() - gray.min(), 1) * 255
    lit = gray > otsu(gray.astype(np.uint8))

    # drop dust and stray reflections: anything far smaller than one pixel block
    from scipy import ndimage
    labels, count = ndimage.label(lit)
    if count:
        sizes = ndimage.sum(lit, labels, range(1, count + 1))
        small = np.isin(labels, np.where(sizes < (scale * scale) * 0.45)[0] + 1)
        lit = lit & ~small

    out = np.zeros((64 * scale, 128 * scale, 3), dtype=np.uint8)
    out[:] = SCREEN
    out[lit] = GLOW
    panel = Image.fromarray(out)

    pad = scale * 4
    frame = Image.new("RGB", (panel.width + pad * 2, panel.height + pad * 2), PAPER)
    ImageDraw.Draw(frame).rounded_rectangle(
        [0, 0, frame.width - 1, frame.height - 1], radius=pad, fill=CASE)
    frame.paste(panel, (pad, pad))
    frame.save(dst)
    print("wrote", os.path.relpath(dst, HERE), frame.size)


if len(sys.argv) > 1:
    SHOTS = os.path.join(HERE, "docs", "assets", "shots")
    for src, name in [("1000015642.jpg", "weather"),
                      ("1000015640.jpg", "usage"),
                      ("1000015641.jpg", "games")]:
        path = os.path.join(SRC, src)
        if os.path.exists(path):
            panel_from_photo(path, os.path.join(SHOTS, name + ".png"))
