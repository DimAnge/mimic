#!/usr/bin/env python3
"""The bracket identity: flat, one ink, no bezel and no glow.

Writes the primary asset names. The earlier set lives in docs/assets/classic/.
"""
import ast
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "docs", "assets")

INK = "#16181A"
INK_2 = "#5B6166"
PAPER = "#E7E9E6"
PAPER_DOT = "#D3D7D2"

# lowercase 5x7 cell font for the wordmark
F = {
    "m": "..... ..... ##### #.#.# #.#.# #.#.# .....",
    "i": "..#.. ..... ..#.. ..#.. ..#.. ..#.. .....",
    "c": "..... ..... .###. #.... #.... .###. .....",
    "a": "..... ..... .###. #...# #...# .####  .....",
    "d": "....# ....# .####  #...# #...# .####  .....",
    "e": "..... ..... .###. #.### ##... .###. .....",
    "s": "..... ..... .#### ##... ...## ####. .....",
    "k": "#.... #.... #..#. ###.. #..#. #...# .....",
    "b": "#.... #.... ####. #...# #...# ####. .....",
    "u": "..... ..... #...# #...# #...# .####  .....",
    "y": "..... ..... #...# #...# .#### ...#. .##..",
    " ": "..... ..... ..... ..... ..... ..... .....",
}


# borrow the uppercase set already defined for the classic assets
_src = open(os.path.join(HERE, "tools", "make_assets.py")).read()
for _node in ast.parse(_src).body:
    if isinstance(_node, ast.Assign) and getattr(_node.targets[0], "id", "") == "F":
        _caps = ast.literal_eval(_node.value)
        F = dict(_caps, **F)
        break


def wordmark(s, x0, y0, size, fill=INK, tracking=1):
    parts, x = [], 0
    for ch in s:
        rows = F[ch].split()
        for r, row in enumerate(rows):
            for c, v in enumerate(row):
                if v == "#":
                    parts.append(
                        f'<rect x="{x0+(x+c)*size:.2f}" y="{y0+r*size:.2f}" '
                        f'width="{size+0.4:.2f}" height="{size+0.4:.2f}"/>'
                    )
        x += 5 + tracking
    return f'<g fill="{fill}">' + "".join(parts) + "</g>", (x - tracking) * size, 7 * size


def bracket(S=512, ink=INK, tight=False):
    """The face in brackets. tight=True crops the padding for small sizes."""
    u = S / 100.0
    inset = 6 * u if tight else 11 * u
    t = 7 * u if tight else 6.4 * u
    top = (16 if tight else 24) * u
    bot = (84 if tight else 76) * u
    arm = (14 if tight else 16) * u
    eye = (21 if tight else 19) * u
    ey = (40 if tight else 40) * u
    ex1 = (25 if tight else 27) * u
    ex2 = (54 if tight else 54) * u

    def brk(x, d):
        return (f'<path d="M{x+d*arm:.1f} {top:.1f} H{x:.1f} V{bot:.1f} H{x+d*arm:.1f}" '
                f'fill="none" stroke="{ink}" stroke-width="{t:.1f}"/>')

    return (brk(inset, 1) + brk(S - inset, -1)
            + f'<rect x="{ex1:.1f}" y="{ey:.1f}" width="{eye:.1f}" height="{eye:.1f}" fill="{ink}"/>'
            + f'<rect x="{ex2:.1f}" y="{ey:.1f}" width="{eye:.1f}" height="{eye:.1f}" fill="{ink}"/>')


def svg(w, h, body, label=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{label}">{body}</svg>')


def save(name, content):
    path = os.path.join(OUT, name)
    open(path, "w").write(content)
    print("wrote", os.path.relpath(path, HERE))


# square mark, ink on transparent
save("logo-mark.svg", svg(512, 512, bracket(512), "Mimic"))

# favicon: inverted tile so it holds up in a dark browser tab at 16px
fav = (f'<rect width="64" height="64" rx="10" fill="{INK}"/>'
       + f'<g transform="translate(6,6) scale(0.8125)">{bracket(64, PAPER, tight=True)}</g>')
save("favicon.svg", svg(64, 64, fav, "Mimic"))

# horizontal lockup
MK, PX = 104, 11
wm, ww, wh = wordmark("mimic", MK + 30, 26, PX)
sub, sw, sh = wordmark("desk buddy", MK + 32, 26 + 7 * PX + 12, 4, INK_2)
save("logo.svg", svg(MK + 30 + max(ww, sw) + 6, 150,
                     f'<g transform="translate(0,23) scale(0.2031)">{bracket(512)}</g>{wm}{sub}',
                     "Mimic - desk buddy"))

# wordmark on its own
wm, ww, wh = wordmark("mimic", 0, 0, 16)
save("wordmark.svg", svg(ww, wh, wm, "Mimic"))


# social preview
def social():
    W, H = 1280, 640
    dots = "".join(f'<rect x="{x}" y="{y}" width="2" height="2"/>'
                   for y in range(0, H, 16) for x in range(0, W, 16))
    body = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>',
            f'<g fill="{PAPER_DOT}" opacity="0.9">{dots}</g>']

    # the mark, large, on the right
    size = 420
    body.append(f'<g transform="translate({W-size-104},{(H-size)/2}) '
                f'scale({size/512:.4f})">{bracket(512)}</g>')

    LX, top = 104, 232
    wm, ww, _ = wordmark("mimic", LX, top, 19)
    body.append(wm)
    body.append(f'<rect x="{LX}" y="{top+7*19+30}" width="{ww}" height="3" fill="{INK}" opacity="0.25"/>')
    t1, _, _ = wordmark("A DESK BUDDY", LX, top + 7 * 19 + 58, 6)
    t2, _, _ = wordmark("PICO W / CIRCUITPYTHON / TWO BUTTONS", LX, top + 7 * 19 + 118, 3, INK_2)
    body += [t1, t2]
    return svg(W, H, "".join(body))


save("social-preview.svg", social())

import cairosvg

for src, dst, w, h, bg in [
    ("logo-mark.svg", "logo-mark-512.png", 512, 512, None),
    ("favicon.svg", "favicon-32.png", 32, 32, None),
    ("favicon.svg", "favicon-180.png", 180, 180, None),
    ("social-preview.svg", "social-preview.png", 1280, 640, None),
]:
    cairosvg.svg2png(url=os.path.join(OUT, src), write_to=os.path.join(OUT, dst),
                     output_width=w, output_height=h, background_color=bg)
    print("rendered", dst)
