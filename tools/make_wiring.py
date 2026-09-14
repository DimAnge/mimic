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

W, H = 940, 560
BX, BY, BW, BH = 390, 66, 160, 452          # Pico board
ROWS = [
    ("GP0", "pin 1", W_SDA),
    ("GP1", "pin 2", W_SCL),
    ("GND", "pin 3", W_GND),
    ("3V3", "pin 36", W_VCC),
    ("GP2", "pin 4", W_BTN),
    ("GP3", "pin 5", W_BTN),
    ("GND", "pin 8", W_GND),
    ("GP20", "pin 26", W_BUZ),
]
ROW_Y = [BY + 78 + i * 46 for i in range(len(ROWS))]
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
t(BX + BW / 2, BY + BH - 16, "USB", 11, "#5B6166", anchor="middle", ls=1)

for (name, pin, color), y in zip(ROWS, ROW_Y):
    s.append(f'<rect x="{BX-8}" y="{y-7}" width="8" height="14" rx="2" fill="{GOLD}"/>')
    s.append(f'<rect x="{BX+BW}" y="{y-7}" width="8" height="14" rx="2" fill="{GOLD}"/>')
    t(BX + BW / 2, y - 1, name, 13, "#E7E9E6", anchor="middle", weight=600)
    t(BX + BW / 2, y + 13, pin, 10, "#7C8489", anchor="middle")

# ------------------------------------------------------------- components ----
oled = list(block(70, 92, 200, 172, "SSD1306 OLED  128x64", [
    ("SDA", W_SDA, 0), ("SCL", W_SCL, 1), ("GND", W_GND, 2), ("VCC", W_VCC, 3)], "left"))
for label, color, row, px, py in oled:
    wire(px + 2, py, BX - 8, ROW_Y[row], color, bend=px + 40 + row * 14)

b1 = list(block(672, 92, 198, 118, "BUTTON 1  tab / home", [
    ("leg A", W_BTN, 4), ("leg B", W_GND, 6)], "right"))
for label, color, row, px, py in b1:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 40 - (0 if row == 4 else 22))

b2 = list(block(672, 232, 198, 118, "BUTTON 2  action", [
    ("leg A", W_BTN, 5), ("leg B", W_GND, 6)], "right"))
for label, color, row, px, py in b2:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 62 - (0 if row == 5 else 24))

bz = list(block(672, 372, 198, 148, "PASSIVE BUZZER", [
    ("SIG", W_BUZ, 7), ("VCC", W_VCC, 3), ("GND", W_GND, 6)], "right"))
for label, color, row, px, py in bz:
    wire(px - 2, py, BX + BW + 8, ROW_Y[row], color, bend=px - 84 - row * 6)

# --------------------------------------------------------------- the key -----
t(70, 300, "Every wire is female-to-male Dupont;", 12, INK2)
t(70, 320, "buttons connect one leg to a GPIO pin", 12, INK2)
t(70, 340, "and the other to any ground pin.", 12, INK2)
t(70, 392, "WIRE COLOURS", 11, INK, weight=700, ls=1.4)
key = [("3V3 power", W_VCC), ("Ground", W_GND), ("I2C data", W_SDA),
       ("I2C clock", W_SCL), ("Button input", W_BTN), ("Buzzer signal", W_BUZ)]
for i, (label, color) in enumerate(key):
    y = 416 + i * 22
    s.append(f'<rect x="70" y="{y-8}" width="22" height="4" rx="2" fill="{color}"/>')
    t(102, y - 3, label, 12, INK2)

svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" '
       f'height="{H}" role="img" aria-label="Mimic wiring map">' + "".join(s) + "</svg>")
open(os.path.join(OUT, "wiring.svg"), "w").write(svg)
print("wrote wiring.svg")

import cairosvg
cairosvg.svg2png(url=os.path.join(OUT, "wiring.svg"),
                 write_to=os.path.join(OUT, "wiring.png"), output_width=1400,
                 background_color="#FFFFFF")
print("rendered wiring.png")
