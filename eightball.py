# eightball.py -- the classic Magic 8-Ball, for a 128x64 SSD1306
#
#     from eightball import EightBall
#     ball = EightBall()
#     main_group.append(ball.group)
#     ball.press(sfx)              # shake
#     ball.tick(now, sfx)          # every loop
#
# Three states: waiting, shaking (a short wobble with rattle blips), and
# showing an answer. Pressing again re-shakes.

import time
import random
import displayio
import terminalio
from adafruit_display_text import label

from eyes import _fill as fill_rect

W, H = 128, 64
SHAKE_TIME = 1.1

WAITING, SHAKING, ANSWER = 0, 1, 2

# The canonical twenty, grouped so the buzzer can react to the verdict.
YES = (
    "It is certain",
    "It is decidedly so",
    "Without a doubt",
    "Yes, definitely",
    "You may rely on it",
    "As I see it, yes",
    "Most likely",
    "Outlook good",
    "Yes",
    "Signs point to yes",
)
MAYBE = (
    "Reply hazy, try again",
    "Ask again later",
    "Better not tell you now",
    "Cannot predict now",
    "Concentrate and ask again",
)
NO = (
    "Don't count on it",
    "My reply is no",
    "My sources say no",
    "Outlook not so good",
    "Very doubtful",
)


def _wrap(text, width=21, lines=3):
    """Greedy word wrap into a fixed number of lines."""
    words = text.split()
    out = []
    current = ""
    for word in words:
        candidate = word if not current else current + " " + word
        if len(candidate) <= width:
            current = candidate
        else:
            out.append(current)
            current = word
            if len(out) == lines - 1:
                break
    if current and len(out) < lines:
        out.append(current)
    while len(out) < lines:
        out.append("")
    return out[:lines]


class EightBall:
    def __init__(self):
        self.bitmap = displayio.Bitmap(W, H, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0xFFFFFF

        self.group = displayio.Group()
        self.group.append(displayio.TileGrid(self.bitmap, pixel_shader=palette))

        self.eight = label.Label(terminalio.FONT, text="8", scale=2, x=59, y=34)
        self.hint = label.Label(terminalio.FONT, text="", scale=1, x=0, y=59)
        self.lines = [
            label.Label(terminalio.FONT, text="", scale=1, x=0, y=20),
            label.Label(terminalio.FONT, text="", scale=1, x=0, y=32),
            label.Label(terminalio.FONT, text="", scale=1, x=0, y=44),
        ]
        self.group.append(self.eight)
        for lbl in self.lines:
            self.group.append(lbl)
        self.group.append(self.hint)

        self.state = WAITING
        self.answer = ""
        self.verdict = "maybe"
        self._shake_until = 0.0
        self._jitter = (0, 0)
        self._next_jitter = 0.0
        self.reset()

    # ---------- helpers ----------

    def _centre(self, lbl, text):
        lbl.text = text
        lbl.x = max(0, (W - len(text) * 6) // 2)

    def reset(self):
        self.state = WAITING
        self.answer = ""
        self._jitter = (0, 0)
        self._sync_labels()

    def _sync_labels(self):
        showing_answer = self.state == ANSWER
        self.eight.hidden = showing_answer
        for lbl in self.lines:
            lbl.hidden = not showing_answer
        if self.state == WAITING:
            self._centre(self.hint, "ask, then press 2")
        elif self.state == SHAKING:
            self._centre(self.hint, "shaking...")
        else:
            self._centre(self.hint, "press 2 to ask again")

    # ---------- input ----------

    def press(self, sfx=None):
        now = time.monotonic()
        self.state = SHAKING
        self._shake_until = now + SHAKE_TIME
        self._next_jitter = 0.0
        self.answer = ""
        self._sync_labels()
        if sfx:
            sfx.tone(300, 0.05)

    # ---------- update ----------

    def tick(self, now=None, sfx=None):
        now = now or time.monotonic()

        if self.state == SHAKING:
            if now >= self._next_jitter:
                self._next_jitter = now + 0.07
                self._jitter = (random.randint(-3, 3), random.randint(-2, 2))
                if sfx and random.random() < 0.4:
                    sfx.tone(random.randint(180, 420), 0.03)
            if now >= self._shake_until:
                self._settle(sfx)

        self._draw()

    def _settle(self, sfx):
        roll = random.random()
        if roll < 0.5:
            self.answer = random.choice(YES)
            self.verdict = "yes"
        elif roll < 0.75:
            self.answer = random.choice(NO)
            self.verdict = "no"
        else:
            self.answer = random.choice(MAYBE)
            self.verdict = "maybe"

        self.state = ANSWER
        self._jitter = (0, 0)
        for lbl, text in zip(self.lines, _wrap(self.answer)):
            self._centre(lbl, text)
        self._sync_labels()

        if sfx:
            sfx.play({"yes": "win", "no": "fail"}.get(self.verdict, "select"))

    # ---------- drawing ----------

    def _draw(self):
        bmp = self.bitmap
        fill_rect(bmp, 0, 0, W, H, 0)

        if self.state == ANSWER:
            # a small ball in the corner, so the text gets the whole screen
            self._circle(12, 12, 9, 1)
            self._circle(12, 12, 5, 0)
            return

        cx = 64 + self._jitter[0]
        cy = 32 + self._jitter[1]
        self._circle(cx, cy, 26, 1)      # the ball
        self._circle(cx, cy, 12, 0)      # the white disc the 8 sits on
        self.eight.x = cx - 5
        self.eight.y = cy + 2

    def _circle(self, cx, cy, r, value):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            fill_rect(self.bitmap, cx - dx, cy + dy, cx + dx + 1, cy + dy + 1,
                      value)
