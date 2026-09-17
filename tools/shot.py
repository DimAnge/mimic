#!/usr/bin/env python3
"""Turn a Mimic framebuffer dump into a PNG that matches the site palette.

Two ways in:

    python3 tools/shot.py --paste dump.txt      # one or many dumps from a console log
    python3 tools/shot.py /dev/ttyACM0          # listen on the serial port instead

Options:

    --out DIR       where to write (default docs/assets/shots)
    --name NAME     base filename (default the timestamp)
    --scale N       pixel size, default 4
    --bezel         wrap it in the rounded case, like the site
    --raw           plain black and white instead of the OLED palette

Needs Pillow. pyserial only for the serial mode.
"""

import argparse
import datetime
import os
import re
import sys

from PIL import Image, ImageDraw

START = "---MIMIC-SHOT-START---"
END = "---MIMIC-SHOT-END---"

GLOW = (191, 227, 255)
SCREEN = (8, 10, 12)
CASE = (22, 24, 26)


def read_serial(port, baud=115200, timeout=30):
    try:
        import serial
    except ImportError:
        sys.exit("pyserial is not installed: pip install pyserial")
    lines, capturing = [], False
    with serial.Serial(port, baud, timeout=1) as ser:
        print("Waiting for a dump. Press 's' in the serial console...")
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
        while datetime.datetime.now() < deadline:
            line = ser.readline().decode("utf-8", "replace").strip()
            if not line:
                continue
            if line == START:
                lines, capturing = [], True
                continue
            if line == END and capturing:
                return lines
            if capturing:
                lines.append(line)
    sys.exit("Timed out. Is code.py calling screenshot.requested()?")


DIMS = re.compile(r"^(\d+)\s+(\d+)$")
HEXLINE = re.compile(r"^[0-9a-fA-F]+$")


def _clean(block):
    """Keep only the size line and the hex, ignoring console noise."""
    lines, dims = [], None
    for raw in block.splitlines():
        line = raw.strip().replace("\r", "")
        line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
        if dims is None and DIMS.match(line):
            dims = line
        elif dims is not None and HEXLINE.match(line):
            lines.append(line)
    return [dims] + lines if dims else []


def read_paste(path):
    """Every dump in the file, in order. A tio log can hold a whole session."""
    text = open(path, encoding="utf-8", errors="replace").read()
    blocks = []
    for chunk in text.split(START)[1:]:
        block = chunk.split(END, 1)[0]
        cleaned = _clean(block)
        if cleaned:
            blocks.append(cleaned)
    if not blocks:
        sys.exit("No dump found in %s. Look for the START and END markers." % path)
    return blocks


def decode(lines):
    width, height = (int(n) for n in lines[0].split())
    stride = (width + 7) // 8
    data = "".join(lines[1:])
    expected = stride * height * 2
    if len(data) < expected:
        sys.exit("Dump is short: got %d hex chars, expected %d" % (len(data), expected))
    raw = bytes.fromhex(data[:expected])

    img = Image.new("1", (width, height))
    px = img.load()
    for y in range(height):
        base = y * stride
        for x in range(width):
            px[x, y] = 1 if raw[base + (x >> 3)] & (0x80 >> (x & 7)) else 0
    return img


def colourise(img, raw=False):
    out = Image.new("RGB", img.size, (255, 255, 255) if raw else SCREEN)
    lit = (0, 0, 0) if raw else GLOW
    px, dst = img.load(), out.load()
    for y in range(img.height):
        for x in range(img.width):
            if px[x, y]:
                dst[x, y] = lit
    return out


def bezel(img, pad=14, radius=14):
    w, h = img.width + pad * 2, img.height + pad * 2
    case = Image.new("RGB", (w, h), (231, 233, 230))
    d = ImageDraw.Draw(case)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=CASE)
    case.paste(img, (pad, pad))
    return case


def main():
    p = argparse.ArgumentParser()
    p.add_argument("port", nargs="?", help="serial port, e.g. /dev/ttyACM0")
    p.add_argument("--paste", help="a saved console dump instead of a live port")
    p.add_argument("--out", default="docs/assets/shots")
    p.add_argument("--name", help="base filename when there is one dump")
    p.add_argument("--names", help="comma-separated names, in capture order: "
                                   "face,weather,calendar,spotify,system,timer,usage,games")
    p.add_argument("--scale", type=int, default=4)
    p.add_argument("--bezel", action="store_true")
    p.add_argument("--raw", action="store_true")
    a = p.parse_args()

    if a.paste:
        blocks = read_paste(a.paste)
    elif a.port:
        blocks = [read_serial(a.port)]
    else:
        p.error("give a serial port or --paste FILE")

    os.makedirs(a.out, exist_ok=True)
    base = a.name or datetime.datetime.now().strftime("shot-%Y%m%d-%H%M%S")
    names = [n.strip() for n in a.names.split(",")] if a.names else []

    for i, lines in enumerate(blocks):
        img = colourise(decode(lines), raw=a.raw)
        if a.scale > 1:
            img = img.resize((img.width * a.scale, img.height * a.scale), Image.NEAREST)
        if a.bezel:
            img = bezel(img, pad=a.scale * 4, radius=a.scale * 4)
        if i < len(names):
            name = names[i]
        elif len(blocks) > 1:
            name = "%s-%d" % (base, i + 1)
        else:
            name = base
        path = os.path.join(a.out, name + ".png")
        img.save(path)
        print("wrote", path, img.size)

    if len(blocks) > 1:
        print("%d screens captured" % len(blocks))


if __name__ == "__main__":
    main()
