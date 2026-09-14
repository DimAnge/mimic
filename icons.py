# icons.py -- 28x28 monochrome weather sprites drawn with rectangle fills
#
#     from icons import draw_weather
#     draw_weather(bitmap, "10d")      # OpenWeather icon code
#
# Codes come straight from the API (d["weather"][0]["icon"]): 01 clear,
# 02 few clouds, 03/04 cloudy, 09/10 rain, 11 storm, 13 snow, 50 mist.
# The trailing d/n picks sun or moon.

from eyes import _fill as fill_rect

SIZE = 28


def _circle(bmp, cx, cy, r, value=1):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        fill_rect(bmp, cx - dx, cy + dy, cx + dx + 1, cy + dy + 1, value)


def _clear(bmp):
    fill_rect(bmp, 0, 0, SIZE, SIZE, 0)


def _sun(bmp, cx=14, cy=13, r=6):
    _circle(bmp, cx, cy, r)
    fill_rect(bmp, cx - 1, cy - r - 5, cx + 1, cy - r - 2, 1)      # N
    fill_rect(bmp, cx - 1, cy + r + 2, cx + 1, cy + r + 5, 1)      # S
    fill_rect(bmp, cx - r - 5, cy - 1, cx - r - 2, cy + 1, 1)      # W
    fill_rect(bmp, cx + r + 2, cy - 1, cx + r + 5, cy + 1, 1)      # E
    for ox, oy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):            # diagonals
        x = cx + ox * (r + 2)
        y = cy + oy * (r + 2)
        fill_rect(bmp, x - 1, y - 1, x + 2, y + 2, 1)


def _moon(bmp, cx=15, cy=13, r=8):
    _circle(bmp, cx, cy, r, 1)
    _circle(bmp, cx - 5, cy - 3, r - 1, 0)      # bite out of it = crescent


def _cloud(bmp, y_off=0, small=False):
    if small:
        _circle(bmp, 12, 17 + y_off, 4)
        _circle(bmp, 18, 16 + y_off, 5)
        _circle(bmp, 22, 18 + y_off, 3)
        fill_rect(bmp, 9, 17 + y_off, 25, 22 + y_off, 1)
    else:
        _circle(bmp, 9, 16 + y_off, 5)
        _circle(bmp, 16, 14 + y_off, 7)
        _circle(bmp, 22, 17 + y_off, 4)
        fill_rect(bmp, 5, 16 + y_off, 26, 22 + y_off, 1)


def _rain(bmp, heavy=False):
    _cloud(bmp, y_off=-4)
    for i, x in enumerate((7, 14, 21)):
        for step in range(4 if heavy else 3):
            fill_rect(bmp, x - step, 21 + step, x - step + 2, 23 + step, 1)


def _snow(bmp):
    _cloud(bmp, y_off=-4)
    for x in (8, 15, 22):
        fill_rect(bmp, x, 23, x + 3, 26, 1)


def _storm(bmp):
    _cloud(bmp, y_off=-5)
    # zig-zag bolt, drawn as three stepped bars
    fill_rect(bmp, 15, 19, 19, 22, 1)
    fill_rect(bmp, 12, 22, 17, 25, 1)
    fill_rect(bmp, 14, 25, 17, 28, 1)


def _mist(bmp):
    for i, y in enumerate((8, 13, 18, 23)):
        left = 3 + (i % 2) * 4
        right = 25 - ((i + 1) % 2) * 4
        fill_rect(bmp, left, y, right, y + 2, 1)


def draw_weather(bmp, code):
    """Render an OpenWeather icon code into a 28x28 bitmap."""
    _clear(bmp)
    if not code:
        _cloud(bmp)
        return
    kind = code[:2]
    night = code.endswith("n")

    if kind == "01":
        _moon(bmp) if night else _sun(bmp)
    elif kind == "02":
        if night:
            _moon(bmp, cx=9, cy=9, r=6)
        else:
            _sun(bmp, cx=9, cy=8, r=4)
        _cloud(bmp, y_off=2, small=True)
    elif kind in ("03", "04"):
        _cloud(bmp)
    elif kind == "09":
        _rain(bmp, heavy=True)
    elif kind == "10":
        _rain(bmp)
    elif kind == "11":
        _storm(bmp)
    elif kind == "13":
        _snow(bmp)
    elif kind == "50":
        _mist(bmp)
    else:
        _cloud(bmp)
