#!/usr/bin/env python3
"""Alternative Mimic logo directions — flatter, rougher, less product-launch.

Writes into docs/assets/alt/ so the original set stays untouched.
Directions:
  bracket  a face held in square brackets, one ink, no bezel, no glow
  stamp    a rubber-stamped badge with a broken edge and ink bleed
  sketch   the device drawn in a wobbly single line, like a notebook margin
"""
import math
import os
import random

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "docs", "assets", "alt")
os.makedirs(OUT, exist_ok=True)

INK = "#16181A"
random.seed(7)

# 5x7 cell font, lowercase for the wordmark
F = {
    "m": "..... ..... ##### #.#.# #.#.# #.#.# .....",
    "i": "..#.. ..... ..#.. ..#.. ..#.. ..#.. .....",
    "c": "..... ..... .###. #.... #.... .###. .....",
}


def text_px(s, tracking=1):
    px, x = [], 0
    for ch in s:
        rows = F[ch].split()
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    px.append((x + c, r))
        x += 5 + tracking
    return px, x - tracking


def wordmark(s, x0, y0, size, fill=INK, tracking=1, jitter=0.0):
    px, w = text_px(s, tracking)
    parts = []
    for c, r in px:
        jx = random.uniform(-jitter, jitter)
        jy = random.uniform(-jitter, jitter)
        parts.append(
            f'<rect x="{x0+c*size+jx:.2f}" y="{y0+r*size+jy:.2f}" '
            f'width="{size+0.4:.2f}" height="{size+0.4:.2f}"/>'
        )
    return f'<g fill="{fill}">' + "".join(parts) + "</g>", w * size, 7 * size


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{label}">'
            + body + "</svg>")


def save(name, content):
    open(os.path.join(OUT, name), "w").write(content)


# --------------------------------------------------------------- bracket ----
def bracket_mark(S=512):
    u = S / 100.0
    b, t = 11 * u, 6.4 * u                 # bracket inset, stroke thickness
    top, bot = 24 * u, 76 * u
    def brk(x, dirn):
        return (f'<path d="M{x+dirn*16*u} {top} H{x} V{bot} H{x+dirn*16*u}" fill="none" '
                f'stroke="{INK}" stroke-width="{t}" stroke-linecap="butt"/>')
    eye = 19 * u
    body = [
        brk(b, 1), brk(S - b, -1),
        f'<rect x="{27*u}" y="{40*u}" width="{eye}" height="{eye}" fill="{INK}"/>',
        f'<rect x="{54*u}" y="{40*u}" width="{eye}" height="{eye}" fill="{INK}"/>',
    ]
    return "".join(body)


save("bracket-mark.svg", svg(512, 512, bracket_mark(), "Mimic"))
wm, ww, wh = wordmark("mimic", 150, 26, 13, tracking=1)
save("bracket-logo.svg", svg(150 + ww + 6, 130,
     f'<g transform="translate(8,9) scale(0.2168)">{bracket_mark()}</g>' + wm, "Mimic"))


# ----------------------------------------------------------------- stamp ----
def rough_circle(cx, cy, r, wobble=1.6, gaps=((0.42, 0.06), (1.62, 0.05), (3.9, 0.07))):
    """A ring drawn as short arcs with wobble and a few missing bites."""
    segs, step = [], 0.045
    a = 0.0
    while a < math.tau:
        skip = any(g[0] <= a <= g[0] + g[1] for g in gaps)
        if not skip:
            rr = r + random.uniform(-wobble, wobble)
            x1, y1 = cx + rr * math.cos(a), cy + rr * math.sin(a)
            rr2 = r + random.uniform(-wobble, wobble)
            x2, y2 = cx + rr2 * math.cos(a + step), cy + rr2 * math.sin(a + step)
            segs.append(f'M{x1:.1f} {y1:.1f} L{x2:.1f} {y2:.1f}')
        a += step
    return f'<path d="{" ".join(segs)}" fill="none" stroke="{INK}" stroke-width="{r*0.085:.1f}" stroke-linecap="round"/>'


def stamp_mark(S=512):
    u = S / 100.0
    cx = cy = S / 2
    body = [rough_circle(cx, cy, 44 * u)]
    # face: two eyes and a flat mouth, all slightly off-register
    for dx in (-13, 11):
        body.append(f'<rect x="{cx+dx*u-0.6*u:.1f}" y="{cy-14*u:.1f}" width="{9*u:.1f}" '
                    f'height="{11*u:.1f}" rx="{1.5*u:.1f}" fill="{INK}"/>')
    body.append(f'<rect x="{cx-13*u:.1f}" y="{cy+8*u:.1f}" width="{25*u:.1f}" height="{3.4*u:.1f}" fill="{INK}"/>')
    # ink specks
    for _ in range(22):
        a = random.uniform(0, math.tau)
        rr = random.uniform(30, 52) * u
        body.append(f'<circle cx="{cx+rr*math.cos(a):.1f}" cy="{cy+rr*math.sin(a):.1f}" '
                    f'r="{random.uniform(0.3,1.1)*u:.1f}" fill="{INK}" opacity="{random.uniform(.25,.8):.2f}"/>')
    return "".join(body)


save("stamp-mark.svg", svg(512, 512, stamp_mark(), "Mimic"))
wm, ww, wh = wordmark("mimic", 132, 30, 12, tracking=1, jitter=0.7)
save("stamp-logo.svg", svg(132 + ww + 6, 124,
     f'<g transform="translate(4,4) scale(0.2266)">{stamp_mark()}</g>' + wm, "Mimic"))


# ---------------------------------------------------------------- sketch ----
def wob(pts, amp=1.7):
    return " ".join(f"{'M' if i == 0 else 'L'}{x+random.uniform(-amp,amp):.1f} "
                    f"{y+random.uniform(-amp,amp):.1f}" for i, (x, y) in enumerate(pts))


def dense(a, b, n=9):
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]


def box(x, y, w, h, amp=1.7):
    pts = (dense((x, y), (x + w, y)) + dense((x + w, y), (x + w, y + h))
           + dense((x + w, y + h), (x, y + h)) + dense((x, y + h), (x, y)) + [(x, y)])
    return f'<path d="{wob(pts, amp)}" fill="none" stroke="{INK}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>'


def sketch_mark(S=512):
    u = S / 100.0
    body = [box(10 * u, 22 * u, 80 * u, 56 * u)]          # the case
    body.append(box(18 * u, 30 * u, 64 * u, 32 * u, amp=0.8))   # the screen
    for dx in (30, 53):                                    # eyes, scribbled solid
        lines = []
        for i in range(16):
            yy = 36 * u + i * 0.92 * u
            lines.append(f'M{dx*u+random.uniform(-1.2,1.2):.1f} {yy:.1f} '
                         f'L{(dx+12)*u+random.uniform(-1.2,1.2):.1f} {yy+random.uniform(-1,1):.1f}')
        body.append(f'<path d="{" ".join(lines)}" fill="none" stroke="{INK}" stroke-width="3.4" stroke-linecap="round"/>')
    for dx in (32, 58):                                    # the two buttons
        body.append(f'<path d="{wob(dense((dx*u, 70*u), ((dx+10)*u, 70*u), 6), 1.2)}" '
                    f'fill="none" stroke="{INK}" stroke-width="5" stroke-linecap="round"/>')
    # usb cable wandering off the right edge
    c = [(90 * u, 50 * u), (95 * u, 47 * u), (99 * u, 53 * u)]
    body.append(f'<path d="{wob(c, 1.0)}" fill="none" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>')
    return "".join(body)


save("sketch-mark.svg", svg(512, 512, sketch_mark(), "Mimic"))
wm, ww, wh = wordmark("mimic", 138, 30, 12, tracking=1, jitter=0.9)
save("sketch-logo.svg", svg(138 + ww + 6, 124,
     f'<g transform="translate(2,-6) scale(0.2461)">{sketch_mark()}</g>' + wm, "Mimic"))

# ------------------------------------------------------------- comparison ---
import cairosvg
from PIL import Image

names = ["bracket", "stamp", "sketch"]
for n in names:
    cairosvg.svg2png(url=os.path.join(OUT, n + "-mark.svg"),
                     write_to=os.path.join(OUT, n + "-mark.png"),
                     output_width=512, background_color="#E7E9E6")
    cairosvg.svg2png(url=os.path.join(OUT, n + "-logo.svg"),
                     write_to=os.path.join(OUT, n + "-logo.png"),
                     output_width=640, background_color="#E7E9E6")

sheet = Image.new("RGB", (1040, 3 * 300 + 40), "#E7E9E6")
for i, n in enumerate(names):
    m = Image.open(os.path.join(OUT, n + "-mark.png")).convert("RGB").resize((240, 240))
    l = Image.open(os.path.join(OUT, n + "-logo.png")).convert("RGB")
    l = l.resize((600, int(l.height * 600 / l.width)))
    sheet.paste(m, (30, 30 + i * 300))
    sheet.paste(l, (330, 30 + i * 300 + (240 - l.height) // 2))
sheet.save("/tmp/alt-logos.png")
print("wrote alt set and /tmp/alt-logos.png")
