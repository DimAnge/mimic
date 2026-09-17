#!/usr/bin/env python3
"""Draw the Mimic wiring map as an SVG (font-independent layout, monospace labels)."""
import os

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "assets")

INK, INK2, RULE = "#16181A", "#5B6166", "#C6CAC5"
CASE, GOLD = "#16181A", "#D8B55A"
W_SDA, W_SCL, W_VCC, W_GND, W_BTN, W_BUZ = (
    "#2E6FD9", "#E0A100", "#D0342C", "#3A3F44", "#2E9E5B", "#7A4FC0",
)
MONO = "ui-monospace, 'IBM Plex Mono', 'SFMono-Regular', Menlo, Consolas, monospace"

W, H = 960, 580
BX, BY, BW, BH = 380, 46, 180, 494          # Pico board
ROWS = [
    ("GP0", "pin 1 / 1a", W_SDA),
    ("GP1", "pin 2 / 2a", W_SCL),
    ("GND", "pin 3 / 3a", W_GND),
    ("GP2", "pin 4 / 4a", W_BTN),
    ("GP3", "pin 5 / 5a", W_BTN),
    ("GND", "pin 8 / 8a", W_GND),
    ("GND", "pin 18 / 18a", W_GND),
    ("GP15", "pin 20 / 20a", W_BUZ),
    ("3V3", "pin 36 / 5j", W_VCC),
    ("GND", "pin 38 / 3j", W_GND),
    ("VBUS", "pin 40 / 1j", W_VCC),
]
ROW_Y = [BY + 76 + i * 38 for i in range(len(ROWS))]
s = []


def t(x, y, txt, size=13, fill=INK, anchor="start", weight=400, ls=0):
    s.append(
        f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}" letter-spacing="{ls}">{txt}</text>'
    )


def wire(x1, y1, x2, y2, color, bend=None):
    bx = bend if bend is not None else (x1 + x2) / 2
    s.append(
        f'<path d="M{x1} {y1} H{bx} V{y2} H{x2}" fill="none" stroke="{color}" '
        f'stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    s.append(f'<circle cx="{x2}" cy="{y2}" r="3.6" fill="{color}"/>')
    s.append(f'<circle cx="{x1}" cy="{y1}" r="3.6" fill="{color}"/>')


def block(x, y, w, h, title, ports, side):
    """ports: list of (label, colour, row_index). side = 'left' or 'right'."""
    s.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="#FFFFFF" '
        f'stroke="{INK}" stroke-width="2"/>'
    )
    t(x + 14, y + 24, title, 13, INK, weight=600, ls=0.6)
    s.append(f'<line x1="{x}" y1="{y+36}" x2="{x+w}" y2="{y+36}" stroke="{RULE}" stroke-width="1.5"/>')
    px = x + w if side == "left" else x
    for i, (label, color, row) in enumerate(ports):
        py = y + 60 + i * 30
        t(x + 14 if side == "left" else x + w - 14, py + 4, label, 12, INK2,
          anchor="start" if side == "left" else "end")
        s.append(f'<rect x="{px-6 if side=="left" else px-2}" y="{py-4}" width="8" height="8" fill="{color}"/>')
        yield label, color, row, px, py


# ---------------------------------------------------------------- the board --
s.append(f'<rect width="{W}" height="{H}" fill="none"/>')
s.append(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="12" fill="{CASE}"/>')
s.append(f'<rect x="{BX+6}" y="{BY+6}" width="{BW-12}" height="{BH-12}" rx="8" fill="none" stroke="#2E3337" stroke-width="2"/>')
s.append(f'<rect x="{BX+38}" y="{BY-9}" width="84" height="18" rx="4" fill="#2E3337"/>')
t(BX + BW / 2, BY + 30, "PICO W", 14, "#E7E9E6", anchor="middle", weight=700, ls=1.5)

for (name, pin, color), y in zip(ROWS, ROW_Y):
    s.append(f'<rect x="{BX-8}" y="{y-7}" width="8" height="14" rx="2" fill="{GOLD}"/>')
    s.append(f'<rect x="{BX+BW}" y="{y-7}" width="8" height="14" rx="2" fill="{GOLD}"/>')
    t(BX + BW / 2, y - 1, name, 13, "#E7E9E6", anchor="middle", weight=600)
    t(BX + BW / 2, y + 12, pin, 9, "#7C8489", anchor="middle")

# ------------------------------------------------------------- components ----
oled = list(block(60, 96, 210, 172, "SSD1306 OLED  128x64", [
    ("SDA  1a", W_SDA, 0), ("SCL  2a", W_SCL, 1),
    ("GND  3j", W_GND, 9), ("VCC  5j", W_VCC, 8)], "left"))
for label, color, row, px, py in oled:
    wire(px + 2, py, BX - 8, ROW_Y[row], color, bend=px + 26 + row * 7)

b1 = list(block(680, 80, 200, 118, "BUTTON 1  tab / home", [
    ("leg A  4a", W_BTN, 3), ("leg B  3a", W_GND, 2)], "right"))
for label, color, row, px, py in b1:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 30 - row * 8)

b2 = list(block(680, 226, 200, 118, "BUTTON 2  action", [
    ("leg A  5a", W_BTN, 4), ("leg B  8a", W_GND, 5)], "right"))
for label, color, row, px, py in b2:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 30 - row * 8)

bz = list(block(680, 372, 200, 148, "PASSIVE BUZZER", [
    ("SIG  20a", W_BUZ, 7), ("VCC  1j  5V", W_VCC, 10), ("GND  18a", W_GND, 6)], "right"))
for label, color, row, px, py in bz:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 30 - row * 8)

# --------------------------------------------------------------- the key -----
t(60, 306, "Holes are half-size breadboard rows.", 12, INK2)
t(60, 326, "The Pico straddles the channel: row n", 12, INK2)
t(60, 346, "on side a is pin n, on side j is 41-n.", 12, INK2)
t(60, 398, "WIRE COLOURS", 11, INK, weight=700, ls=1.4)
key = [("Power: 3V3, or 5V for the buzzer", W_VCC), ("Ground", W_GND), ("I2C data", W_SDA),
       ("I2C clock", W_SCL), ("Button input", W_BTN), ("Buzzer signal", W_BUZ)]
for i, (label, color) in enumerate(key):
    y = 422 + i * 22
    s.append(f'<rect x="60" y="{y-8}" width="22" height="4" rx="2" fill="{color}"/>')
    t(92, y - 3, label, 12, INK2)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
       f'height="{H}" role="img" aria-label="Mimic wiring map">' + "".join(s) + "</svg>")
open(os.path.join(OUT, "wiring.svg"), "w").write(svg)
print("wrote wiring.svg")

import cairosvg
cairosvg.svg2png(url=os.path.join(OUT, "wiring.svg"),
                 write_to=os.path.join(OUT, "wiring.png"), output_width=1400,
                 background_color="#FFFFFF")
print("rendered wiring.png")
