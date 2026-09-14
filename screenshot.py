"""Dump the Mimic framebuffer over USB serial.

Press "s" in the serial console (tio /dev/ttyACM0) and the board prints the
current screen as hex between two markers. tools/shot.py on the PC turns that
back into a PNG.

Usage in code.py:

    import screenshot
    ...
    if screenshot.requested():
        screenshot.dump(face_bitmap)   # any displayio.Bitmap you draw into

This only works for a Bitmap you own. See tools/shot.py for what to do if the
screen is built from Label objects instead.
"""

import sys

import supervisor

START = "---MIMIC-SHOT-START---"
END = "---MIMIC-SHOT-END---"
HEX = "0123456789abcdef"


def requested(key="s"):
    """True when the given key has been typed in the serial console."""
    if supervisor.runtime.serial_bytes_available:
        return sys.stdin.read(1).lower() == key
    return False


def dump(bitmap, threshold=1):
    """Print bitmap as packed 1-bit rows, 128 hex characters per line.

    threshold: pixel values >= this count as lit. Leave at 1 for a 1-bit
    bitmap; raise it if you use a palette with more than two entries.
    """
    width, height = bitmap.width, bitmap.height
    stride = (width + 7) // 8
    row = bytearray(stride)

    print(START)
    print("%d %d" % (width, height))
    out = []
    for y in range(height):
        for i in range(stride):
            row[i] = 0
        for x in range(width):
            if bitmap[x, y] >= threshold:
                row[x >> 3] |= 0x80 >> (x & 7)
        for byte in row:
            out.append(HEX[byte >> 4])
            out.append(HEX[byte & 0x0F])
        if len(out) >= 128:
            print("".join(out))
            out = []
    if out:
        print("".join(out))
    print(END)
