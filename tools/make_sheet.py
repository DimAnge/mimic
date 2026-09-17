#!/usr/bin/env python3
"""Compose the README contact sheet from real screen captures.

    python3 tools/make_sheet.py FACE=docs/assets/shots/face.png \\
                                CALENDAR=docs/assets/shots/calendar.png ...

Panels are laid out two per row in the order given, with a pixel-font caption
under each. Output: docs/assets/screens.png
"""
import ast
import os
import sys

from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "docs", "assets", "screens.png")

PAPER = (231, 233, 230)
INK = (22, 24, 26)
COLS = 2
GAP = 22
PAD = 24
CAP = 26          # caption band under each panel

# reuse the pixel font that the logos are built from
_src = open(os.path.join(HERE, "tools", "make_assets.py")).read()
FONT = {}
for _node in ast.parse(_src).body:
    if isinstance(_node, ast.Assign) and getattr(_node.targets[0], "id", "") == "F":
        FONT = ast.literal_eval(_node.value)
        break


def caption(draw, text, x, y, size=3, fill=INK, tracking=2):
    """Draw text as font-free pixel blocks. Returns width in pixels."""
    cx = 0
    for ch in text:
        rows = FONT.get(ch, FONT.get("?", "")).split()
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    draw.rectangle(
                        [x + (cx + c) * size, y + r * size,
                         x + (cx + c) * size + size - 1, y + r * size + size - 1],
                        fill=fill)
        cx += 5 + tracking
    return (cx - tracking) * size


def main():
    global COLS
    pairs = []
    for arg in sys.argv[1:]:
        if arg.startswith("--cols="):
            COLS = int(arg.split("=", 1)[1])
            continue
        label, _, path = arg.partition("=")
        if not path or not os.path.exists(path):
            sys.exit("missing file for %s: %s" % (label, path))
        pairs.append((label.upper(), path))
    if not pairs:
        sys.exit(__doc__)

    panels = [(label, Image.open(path).convert("RGB")) for label, path in pairs]
    pw, ph = panels[0][1].size
    rows = (len(panels) + COLS - 1) // COLS
    width = PAD * 2 + COLS * pw + (COLS - 1) * GAP
    height = PAD * 2 + rows * (ph + CAP) + (rows - 1) * GAP

    sheet = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(sheet)
    for i, (label, img) in enumerate(panels):
        c, r = i % COLS, i // COLS
        x = PAD + c * (pw + GAP)
        y = PAD + r * (ph + CAP + GAP)
        sheet.paste(img, (x, y))
        caption(draw, label, x + 4, y + ph + 9)

    sheet.save(OUT)
    print("wrote", OUT, sheet.size)


if __name__ == "__main__":
    main()
