#!/usr/bin/env python3
"""Generate Mimic brand assets (logo, favicon, social preview) as pure-geometry SVG.

Every glyph is drawn as 1-bit pixel rectangles from a built-in 5x7 font, so the
assets render identically everywhere without needing a font to be installed.
"""
import os, subprocess, textwrap

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "assets")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- palette ----
PAPER = "#E7E9E6"
PAPER_DOT = "#D3D7D2"
CASE = "#16181A"
CASE_EDGE = "#2E3337"
SCREEN = "#080A0C"
GLOW = "#BFE3FF"
GLOW_DIM = "#6E90AE"
INK = "#16181A"
INK_2 = "#5B6166"

# ------------------------------------------------------------------- font ----
F = {
    " ": "..... ..... ..... ..... ..... ..... .....",
    "A": ".###. #...# #...# ##### #...# #...# #...#",
    "B": "####. #...# #...# ####. #...# #...# ####.",
    "C": ".###. #...# #.... #.... #.... #...# .###.",
    "D": "####. #...# #...# #...# #...# #...# ####.",
    "E": "##### #.... #.... ####. #.... #.... #####",
    "F": "##### #.... #.... ####. #.... #.... #....",
    "G": ".###. #...# #.... #.### #...# #...# .###.",
    "H": "#...# #...# #...# ##### #...# #...# #...#",
    "I": "##### ..#.. ..#.. ..#.. ..#.. ..#.. #####",
    "J": "..### ...#. ...#. ...#. ...#. #..#. .##..",
    "K": "#...# #..#. #.#.. ##... #.#.. #..#. #...#",
    "L": "#.... #.... #.... #.... #.... #.... #####",
    "M": "#...# ##.## #.#.# #...# #...# #...# #...#",
    "N": "#...# ##..# #.#.# #..## #...# #...# #...#",
    "O": ".###. #...# #...# #...# #...# #...# .###.",
    "P": "####. #...# #...# ####. #.... #.... #....",
    "Q": ".###. #...# #...# #...# #.#.# #..#. .##.#",
    "R": "####. #...# #...# ####. #.#.. #..#. #...#",
    "S": ".#### #.... #.... .###. ....# ....# ####.",
    "T": "##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..",
    "U": "#...# #...# #...# #...# #...# #...# .###.",
    "V": "#...# #...# #...# #...# #...# .#.#. ..#..",
    "W": "#...# #...# #...# #.#.# #.#.# ##.## #...#",
    "X": "#...# #...# .#.#. ..#.. .#.#. #...# #...#",
    "Y": "#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..",
    "Z": "##### ....# ...#. ..#.. .#... #.... #####",
    "0": ".###. #...# #..## #.#.# ##..# #...# .###.",
    "1": "..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.",
    "2": ".###. #...# ....# ...#. ..#.. .#... #####",
    "3": "##### ...#. ..##. ....# ....# #...# .###.",
    "4": "...#. ..##. .#.#. #..#. ##### ...#. ...#.",
    "5": "##### #.... ####. ....# ....# #...# .###.",
    "6": "..##. .#... #.... ####. #...# #...# .###.",
    "7": "##### ....# ...#. ..#.. .#... .#... .#...",
    "8": ".###. #...# #...# .###. #...# #...# .###.",
    "9": ".###. #...# #...# .#### ....# ...#. .##..",
    ".": "..... ..... ..... ..... ..... .##.. .##..",
    ",": "..... ..... ..... ..... .##.. .##.. .#...",
    "-": "..... ..... ..... ##### ..... ..... .....",
    "/": "....# ....# ...#. ..#.. .#... #.... #....",
    ":": "..... .##.. .##.. ..... .##.. .##.. .....",
    "!": "..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..",
    "?": ".###. #...# ....# ..##. ..#.. ..... ..#..",
    "'": "..#.. ..#.. ..... ..... ..... ..... .....",
    "x": "..... ..... #...# .#.#. ..#.. .#.#. #...#",
    "+": "..... ..#.. ..#.. ##### ..#.. ..#.. .....",
    "(": "...#. ..#.. .#... .#... .#... ..#.. ...#.",
    ")": ".#... ..#.. ...#. ...#. ...#. ..#.. .#...",
    "\u00b0": ".##.. #..#. .##.. ..... ..... ..... .....",
}


def text_px(s, tracking=1):
    """Return list of (col,row) pixels and total width in cells for a string."""
    px, x = [], 0
    for ch in s:
        rows = F.get(ch, F["?"]).split()
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    px.append((x + c, r))
        x += 5 + tracking
    return px, max(x - tracking, 0)


def text_svg(s, x0, y0, size, fill, gap=0.0, tracking=1):
    px, w = text_px(s, tracking)
    d = size - gap
    parts = [
        f'<rect x="{x0 + c*size:.2f}" y="{y0 + r*size:.2f}" width="{d:.2f}" height="{d:.2f}"/>'
        for c, r in px
    ]
    return f'<g fill="{fill}">' + "".join(parts) + "</g>", w * size, 7 * size


# ------------------------------------------------------------------- face ----
def face_pixels(w=128, h=64, blink=False, look=0):
    """Boolean grid of the Mimic face on a w x h 1-bit screen."""
    g = [[0] * w for _ in range(h)]

    def rrect(x, y, ww, hh, r, on=1):
        for j in range(y, y + hh):
            for i in range(x, x + ww):
                dx = max(x + r - i, i - (x + ww - 1 - r), 0)
                dy = max(y + r - j, j - (y + hh - 1 - r), 0)
                if dx * dx + dy * dy <= r * r:
                    if 0 <= j < h and 0 <= i < w:
                        g[j][i] = on

    ex, ey, es = 26 + look, 14, 26
    if blink:
        for cx in (ex, ex + 50):
            rrect(cx, ey + es // 2 - 3, es, 6, 3)
    else:
        for cx in (ex, ex + 50):
            rrect(cx, ey, es, es, 6)
            rrect(cx + 4, ey + 4, 6, 6, 2, on=0)          # highlight
    # status rule + tab dots
    for i in range(6, w - 6):
        g[52][i] = 1
    for t in range(7):
        cx = 8 + t * 8
        if t == 0:
            for j in range(57, 61):
                for i in range(cx - 2, cx + 2):
                    g[j][i] = 1
        else:
            for j in range(58, 60):
                for i in range(cx - 1, cx + 1):
                    g[j][i] = 1
    return g


def grid_svg(g, x0, y0, s, fill, gap=0.0):
    parts = []
    h, w = len(g), len(g[0])
    for r in range(h):
        c = 0
        while c < w:
            if g[r][c]:
                run = 1
                while c + run < w and g[r][c + run]:
                    run += 1
                bleed = 0.0 if gap else 0.75
                parts.append(
                    f'<rect x="{x0+c*s:.2f}" y="{y0+r*s:.2f}" '
                    f'width="{run*s-gap+bleed:.2f}" height="{s-gap+bleed:.2f}"/>'
                )
                c += run
            else:
                c += 1
    return f'<g fill="{fill}">' + "".join(parts) + "</g>"


# --------------------------------------------------------------- the mark ----
def mark(size=512, grid=True, radius_ratio=0.22):
    """Square app-icon style mark: the case, the screen, the face."""
    u = size / 512.0
    pad = 34 * u
    r = size * radius_ratio
    sw, sh = size - 2 * pad, (size - 2 * pad) * 0.62
    sx, sy = pad, (size - sh) / 2 + 6 * u
    px = sw / 132.0                      # pixel size for a 128x64 screen + margin
    fx, fy = sx + (sw - 128 * px) / 2, sy + (sh - 64 * px) / 2

    g = face_pixels()
    body = [
        f'<rect x="0" y="0" width="{size}" height="{size}" rx="{r}" fill="{CASE}"/>',
        f'<rect x="{1.5*u}" y="{1.5*u}" width="{size-3*u}" height="{size-3*u}" '
        f'rx="{r-1.5*u}" fill="none" stroke="{CASE_EDGE}" stroke-width="{3*u}"/>',
        f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="{10*u}" fill="{SCREEN}"/>',
    ]
    if grid:
        lines = []
        for i in range(0, 129, 8):
            lines.append(f'<line x1="{fx+i*px:.2f}" y1="{fy:.2f}" x2="{fx+i*px:.2f}" y2="{fy+64*px:.2f}"/>')
        for j in range(0, 65, 8):
            lines.append(f'<line x1="{fx:.2f}" y1="{fy+j*px:.2f}" x2="{fx+128*px:.2f}" y2="{fy+j*px:.2f}"/>')
        body.append(
            f'<g stroke="{GLOW}" stroke-width="{0.8*u}" opacity="0.10">' + "".join(lines) + "</g>"
        )
    body.append(grid_svg(g, fx, fy, px, GLOW, gap=0))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" role="img" aria-label="Mimic">'
        + "".join(body)
        + "</svg>"
    )


def write(name, content):
    p = os.path.join(OUT, name)
    with open(p, "w") as f:
        f.write(content)
    print("wrote", p)


# 1. square mark + favicon
write("logo-mark.svg", mark(512))
write("favicon.svg", mark(64, grid=False, radius_ratio=0.18))

# 2. horizontal lockup: mark + MIMIC wordmark
MK, H = 112, 134
px = 11
wm, ww, wh = text_svg("MIMIC", MK + 36, 16, px, INK, tracking=2)
sub, sw_, sh_ = text_svg("DESK BUDDY", MK + 38, 104, 4, INK_2, tracking=2)
W = MK + 36 + max(ww, sw_) + 6
lock = (
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:.0f} {H}" '
    f'width="{W:.0f}" height="{H}" role="img" aria-label="Mimic - desk buddy">'
    f'<g transform="translate(0,11)">{mark(MK).split(">",1)[1].rsplit("</svg>",1)[0]}</g>'
    f'{wm}{sub}</svg>'
)
write("logo.svg", lock)

# 3. wordmark only
px = 16
wm, ww, wh = text_svg("MIMIC", 0, 0, px, INK, tracking=2)
write(
    "wordmark.svg",
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {ww} {wh}" width="{ww}" '
    f'height="{wh}" role="img" aria-label="Mimic">{wm}</svg>',
)


# 4. social preview 1280x640
def social():
    W, H = 1280, 640
    dots = []
    for y in range(0, H, 16):
        for x in range(0, W, 16):
            dots.append(f'<rect x="{x}" y="{y}" width="2" height="2"/>')
    body = [
        f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
        f'<g fill="{PAPER_DOT}" opacity="0.9">' + "".join(dots) + "</g>",
    ]

    # right: the device
    pxs = 4
    sxw, sxh = 128 * pxs + 52, 64 * pxs + 52
    X, Y = W - sxw - 72, (H - sxh) / 2
    body.append(f'<rect x="{X}" y="{Y}" width="{sxw}" height="{sxh}" rx="28" fill="{CASE}"/>')
    body.append(
        f'<rect x="{X+1.5}" y="{Y+1.5}" width="{sxw-3}" height="{sxh-3}" rx="26.5" '
        f'fill="none" stroke="{CASE_EDGE}" stroke-width="3"/>'
    )
    body.append(f'<rect x="{X+18}" y="{Y+18}" width="{sxw-36}" height="{sxh-36}" rx="8" fill="{SCREEN}"/>')
    g = face_pixels()
    fx, fy = X + 26, Y + 26
    body.append(grid_svg(g, fx, fy, pxs, GLOW))

    # left: identity block, optically centred against the device
    LX = 96
    top = 206
    body.append(f'<g transform="translate({LX},{top-104})">{mark(76).split(">",1)[1].rsplit("</svg>",1)[0]}</g>')
    wm, ww, _ = text_svg("MIMIC", LX, top, 15, INK, tracking=2)
    body.append(wm)
    body.append(f'<rect x="{LX}" y="{top+7*15+34}" width="{ww}" height="3" fill="{INK}" opacity="0.2"/>')
    t1, w1, _ = text_svg("A 1-BIT DESK BUDDY", LX, top + 7 * 15 + 62, 4, INK, tracking=2)
    t2, _, _ = text_svg("PICO W / CIRCUITPYTHON", LX, top + 7 * 15 + 118, 3, INK_2, tracking=2)
    t3, _, _ = text_svg("SEVEN SCREENS, TWO BUTTONS", LX, top + 7 * 15 + 154, 3, INK_2, tracking=2)
    body += [t1, t2, t3]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
        + "".join(body)
        + "</svg>"
    )


write("social-preview.svg", social())

# 5. rasterise
import cairosvg

jobs = [
    ("logo-mark.svg", "logo-mark-512.png", 512, 512),
    ("favicon.svg", "favicon-32.png", 32, 32),
    ("favicon.svg", "favicon-180.png", 180, 180),
    ("social-preview.svg", "social-preview.png", 1280, 640),
]
for src, dst, w, h in jobs:
    cairosvg.svg2png(
        url=os.path.join(OUT, src), write_to=os.path.join(OUT, dst),
        output_width=w, output_height=h,
    )
    print("rendered", dst)
