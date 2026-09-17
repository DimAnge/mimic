"""Dump the current Mimic screen over USB serial.

The SSD1306 cannot be read back (fill_row needs a 16-bit colourspace), so this
walks display.root_group instead and redraws it into a 1-bit framebuffer: every
label, icon and bitmap is a TileGrid, and a TileGrid knows its own pixels.

Usage in code.py:

    import screenshot
    ...
    # inside the main loop, once per pass
    if screenshot.requested():
        screenshot.dump(display)

Then, on the PC:

    tio /dev/ttyACM0        # press "s" to capture the screen you are looking at
    python3 tools/shot.py /dev/ttyACM0 --bezel

Capture takes a moment and the screen freezes while it runs. That is expected.
"""

import sys

import displayio
import supervisor

START = "---MIMIC-SHOT-START---"
END = "---MIMIC-SHOT-END---"
HEX = "0123456789abcdef"


def requested(key="s"):
    """True when the given key has been typed into the serial console."""
    if supervisor.runtime.serial_bytes_available:
        return sys.stdin.read(1).lower() == key
    return False


def _blit(tg, ox, oy, scale, fb, w, h):
    """Draw one TileGrid into the framebuffer. Index 0 counts as transparent."""
    bitmap = tg.bitmap
    tw, th = tg.tile_width, tg.tile_height
    cols = bitmap.width // tw if tw else 1
    if cols < 1:
        cols = 1
    stride = (w + 7) // 8

    for ty in range(tg.height):
        for tx in range(tg.width):
            try:
                index = tg[tx, ty]
            except (IndexError, TypeError):
                index = 0
            sx = (index % cols) * tw
            sy = (index // cols) * th
            if sy + th > bitmap.height:
                continue
            bx = ox + (tg.x + tx * tw) * scale
            by = oy + (tg.y + ty * th) * scale
            for y in range(th):
                py0 = by + y * scale
                if py0 >= h or py0 + scale <= 0:
                    continue
                for x in range(tw):
                    if not bitmap[sx + x, sy + y]:
                        continue
                    px0 = bx + x * scale
                    for dy in range(scale):
                        py = py0 + dy
                        if py < 0 or py >= h:
                            continue
                        row = py * stride
                        for dx in range(scale):
                            px = px0 + dx
                            if 0 <= px < w:
                                fb[row + (px >> 3)] |= 0x80 >> (px & 7)


def _walk(node, ox, oy, scale, fb, w, h):
    if getattr(node, "hidden", False):
        return
    if isinstance(node, displayio.TileGrid):
        _blit(node, ox, oy, scale, fb, w, h)
        return
    try:
        children = list(node)
    except TypeError:
        return
    inner = scale * getattr(node, "scale", 1)
    x = ox + getattr(node, "x", 0) * scale
    y = oy + getattr(node, "y", 0) * scale
    for child in children:
        _walk(child, x, y, inner, fb, w, h)


def capture(display):
    """Return (framebuffer, width, height) for whatever is on screen now."""
    w, h = display.width, display.height
    fb = bytearray(((w + 7) // 8) * h)
    root = display.root_group
    if root is not None:
        _walk(root, 0, 0, 1, fb, w, h)
    return fb, w, h


def dump(display):
    """Print the current screen as hex, ready for tools/shot.py."""
    fb, w, h = capture(display)
    print(START)
    print("%d %d" % (w, h))
    out = []
    for byte in fb:
        out.append(HEX[byte >> 4])
        out.append(HEX[byte & 0x0F])
        if len(out) >= 128:
            print("".join(out))
            out = []
    if out:
        print("".join(out))
    print(END)


def preview(display):
    """Print the screen as text. Useful when a dump comes out blank."""
    fb, w, h = capture(display)
    stride = (w + 7) // 8
    for y in range(h):
        row = y * stride
        print("".join("#" if fb[row + (x >> 3)] & (0x80 >> (x & 7)) else "."
                      for x in range(w)))
