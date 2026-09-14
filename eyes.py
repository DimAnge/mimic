# eyes.py -- animated face for a 128x64 SSD1306 under displayio (CircuitPython)
#
# Usage:
#     from eyes import Eyes
#     eyes = Eyes()
#     main_group.append(eyes.group)
#     eyes.intro()                       # optional: open from closed
#     while True:
#         eyes.tick()                    # call as often as you can, ~20-30x/sec
#
# Everything is drawn into a single 1-bit Bitmap, so there is no per-frame
# object allocation and the garbage collector stays out of the way.

import time
import random
import displayio

try:
    from bitmaptools import fill_region as _fill_region

    def _fill(bmp, x1, y1, x2, y2, value):
        w, h = bmp.width, bmp.height
        if x1 < 0: x1 = 0
        if y1 < 0: y1 = 0
        if x2 > w: x2 = w
        if y2 > h: y2 = h
        if x2 > x1 and y2 > y1:
            _fill_region(bmp, x1, y1, x2, y2, value)

except ImportError:  # slow fallback if bitmaptools is missing
    def _fill(bmp, x1, y1, x2, y2, value):
        w, h = bmp.width, bmp.height
        if x1 < 0: x1 = 0
        if y1 < 0: y1 = 0
        if x2 > w: x2 = w
        if y2 > h: y2 = h
        for y in range(y1, y2):
            for x in range(x1, x2):
                bmp[x, y] = value


class Eyes:
    MOODS = ("neutral", "happy", "sad", "angry", "sleepy", "surprised", "love")

    # blink timing, seconds
    _CLOSE = 0.07
    _HOLD = 0.04
    _OPEN = 0.12

    _BREATH_PERIOD = 3.6      # slow 1px rise and fall, like breathing

    def __init__(self, width=128, height=64,
                 eye_w=32, eye_h=32, gap=18, radius=9):
        self.W = width
        self.H = height
        self.eye_w = eye_w
        self.eye_h = eye_h
        self.gap = gap
        self.radius = radius

        self.bitmap = displayio.Bitmap(width, height, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0xFFFFFF
        self.group = displayio.Group()
        self.group.append(displayio.TileGrid(self.bitmap, pixel_shader=palette))

        now = time.monotonic()
        self.mood = "neutral"
        self.idle = True                 # auto blinking + gaze wander
        self.openness = 1.0

        self._blink_t0 = -10.0
        self._next_blink = now + random.uniform(2.0, 5.0)
        self._intro_t0 = -100.0
        self._intro_dur = 1.0
        self._gaze = [0.0, 0.0]
        self._gaze_target = [0.0, 0.0]
        self._gaze_hold_until = 0.0
        self._next_look = now + random.uniform(2.0, 6.0)
        self._pulse = 1.0                # heart-beat scale, love mood only
        self._breath = 0                 # 0 or 1 px, always running
        self._last_key = None

        self._draw()

    # ---------- public API ----------

    def set_mood(self, mood):
        if mood in self.MOODS:
            self.mood = mood

    def blink(self, double=False, now=None):
        now = now or time.monotonic()
        self._blink_t0 = now
        if double:
            self._next_blink = now + 0.30

    def intro(self, duration=1.2, now=None):
        """Open from fully closed -- the boot animation."""
        now = now or time.monotonic()
        self._intro_t0 = now
        self._intro_dur = duration
        self._blink_t0 = -10.0
        self._next_blink = now + duration + 0.9
        self._gaze[0] = self._gaze[1] = 0.0
        self._gaze_target[0] = self._gaze_target[1] = 0.0

    def look(self, dx, dy=0.0, hold=1.2, now=None):
        """Glance somewhere. dx/dy are -1.0 .. 1.0."""
        now = now or time.monotonic()
        self._gaze_target[0] = max(-1.0, min(1.0, dx)) * 9.0
        self._gaze_target[1] = max(-1.0, min(1.0, dy)) * 6.0
        self._gaze_hold_until = now + hold
        self._next_look = self._gaze_hold_until + random.uniform(1.5, 4.0)

    def center(self, now=None):
        self.look(0.0, 0.0, hold=0.6, now=now)

    def startle(self, now=None):
        """Quick 'oh!' -- widen, then settle back to neutral on its own."""
        now = now or time.monotonic()
        self.mood = "surprised"
        self.center(now=now)
        self._mood_revert = now + 0.8

    _mood_revert = 0.0

    # ---------- per-frame update ----------

    def _wander(self, now):
        """Pick somewhere new to look.

        Weighted so most movements are tiny. Constant big sweeps look
        frantic; occasional micro-saccades read as a living thing.
        """
        roll = random.random()
        if roll < 0.35:                       # return to centre
            self._gaze_target[0] = 0.0
            self._gaze_target[1] = 0.0
            self._next_look = now + random.uniform(1.5, 4.0)
        elif roll < 0.75:                     # micro-saccade
            self._gaze_target[0] = random.uniform(-3.0, 3.0)
            self._gaze_target[1] = random.uniform(-2.0, 2.0)
            self._next_look = now + random.uniform(0.6, 2.0)
        else:                                 # proper glance
            self._gaze_target[0] = random.uniform(-9.0, 9.0)
            self._gaze_target[1] = random.uniform(-5.0, 5.0)
            self._next_look = now + random.uniform(1.8, 5.0)

    def tick(self, now=None):
        now = now or time.monotonic()
        intro_elapsed = now - self._intro_t0
        in_intro = intro_elapsed < self._intro_dur

        if self._mood_revert and now > self._mood_revert:
            self._mood_revert = 0.0
            self.mood = "neutral"

        if self.idle and not in_intro:
            if now >= self._next_blink:
                self.blink(double=(random.random() < 0.15), now=now)
                self._next_blink = now + random.uniform(2.5, 6.5)
            if now >= self._next_look and now >= self._gaze_hold_until:
                self._wander(now)

        # ease the gaze toward its target
        for i in (0, 1):
            self._gaze[i] += (self._gaze_target[i] - self._gaze[i]) * 0.28

        if in_intro:
            # ease-in so the lids accelerate open rather than sliding linearly
            p = intro_elapsed / self._intro_dur
            if p < 0.0:
                p = 0.0
            self.openness = p * p
        else:
            e = now - self._blink_t0
            total = self._CLOSE + self._HOLD + self._OPEN
            if e < 0 or e >= total:
                self.openness = 1.0
            elif e < self._CLOSE:
                self.openness = 1.0 - (e / self._CLOSE)
            elif e < self._CLOSE + self._HOLD:
                self.openness = 0.0
            else:
                self.openness = (e - self._CLOSE - self._HOLD) / self._OPEN

        # slow 1px breathing -- subliminal, but the face looks dead without it
        phase = (now % self._BREATH_PERIOD) / self._BREATH_PERIOD
        self._breath = int(1.6 * (1.0 - abs(phase * 2.0 - 1.0)))

        # hearts beat; everything else holds still
        if self.mood == "love":
            beat = (now % 1.1) / 1.1
            self._pulse = 1.0 + 0.12 * (1.0 - abs(beat * 2.0 - 1.0))
        else:
            self._pulse = 1.0

        # only redraw when something visibly changed
        key = (self.mood,
               int(self.openness * 16),
               int(self._gaze[0]),
               int(self._gaze[1]),
               int(self._pulse * 40),
               self._breath)
        if key != self._last_key:
            self._last_key = key
            self._draw()

    # ---------- drawing ----------

    def _draw(self):
        _fill(self.bitmap, 0, 0, self.W, self.H, 0)
        cy = self.H // 2 + int(self._gaze[1])
        span = self.eye_w * 2 + self.gap
        left_x = (self.W - span) // 2 + int(self._gaze[0])
        self._eye(left_x, cy, True)
        self._eye(left_x + self.eye_w + self.gap, cy, False)

    def _eye(self, x, cy, is_left):
        mood = self.mood
        w = self.eye_w
        h = self.eye_h

        if mood == "surprised":
            w = int(w * 0.86)
            h = int(h * 1.12)
        elif mood == "sleepy":
            h = int(h * 0.42)
        elif mood == "love":
            w = int(w * self._pulse)
            h = int(h * self._pulse)

        h = int(h * self.openness)
        if self.openness > 0.9:
            h += self._breath
        if h < 2:
            h = 2

        if mood == "love":
            y = cy - h // 2
            hx = x + (self.eye_w - w) // 2      # keep centred as it beats
            self._heart(hx, y, w, h)
            return

        y = cy - h // 2
        if mood == "sleepy":
            y += 4

        r = min(self.radius, h // 2, w // 2)
        self._rrect(x, y, w, h, r, 1)

        # expressive cut-outs only make sense on a mostly-open eye
        if self.openness < 0.65 or h < 8:
            return

        if mood == "happy":
            # carve a curve out of the bottom, leaving a ^ arc
            cut_y = y + int(h * 0.38)
            self._rrect(x - 2, cut_y, w + 4, h, r, 0)
        elif mood == "angry":
            # inner corner slopes down toward the nose
            self._wedge(x, y, w, int(h * 0.45), thick_left=(not is_left))
        elif mood == "sad":
            # outer corner slopes down
            self._wedge(x, y, w, int(h * 0.45), thick_left=is_left)

    def _heart(self, x, y, w, h, value=1):
        """Two lobes plus a tapering V -- reads as a heart even at 32px."""
        if h < 6 or w < 6:
            _fill(self.bitmap, x, y, x + w, y + h, value)
            return

        r = w // 4
        lobe_cy = y + int(h * 0.32)
        for i in range(-r, r):
            dx = int((r * r - i * i) ** 0.5)
            row = lobe_cy + i
            _fill(self.bitmap, x + r - dx, row, x + r + dx, row + 1, value)
            _fill(self.bitmap, x + w - r - dx, row, x + w - r + dx, row + 1, value)

        mid = x + w // 2
        span = (y + h) - lobe_cy
        if span < 1:
            return
        for i in range(span):
            half = ((w // 2) * (span - i)) // span
            if half <= 0:
                continue
            row = lobe_cy + i
            _fill(self.bitmap, mid - half, row, mid + half, row + 1, value)

    def _rrect(self, x, y, w, h, r, value):
        if r < 1:
            _fill(self.bitmap, x, y, x + w, y + h, value)
            return
        _fill(self.bitmap, x, y + r, x + w, y + h - r, value)
        for i in range(r):
            dy = r - 1 - i
            dx = r - int((r * r - dy * dy) ** 0.5)
            _fill(self.bitmap, x + dx, y + i, x + w - dx, y + i + 1, value)
            _fill(self.bitmap, x + dx, y + h - 1 - i, x + w - dx, y + h - i, value)

    def _wedge(self, x, y, w, h, thick_left):
        """Punch a right triangle out of the top of an eye."""
        if h < 2:
            return
        for i in range(h):
            run = w - (w * i) // h
            if run <= 0:
                continue
            if thick_left:
                _fill(self.bitmap, x, y + i, x + run, y + i + 1, 0)
            else:
                _fill(self.bitmap, x + w - run, y + i, x + w, y + i + 1, 0)
