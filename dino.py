# dino.py -- one-button endless runner for a 128x64 SSD1306
#
#     from dino import DinoGame
#     game = DinoGame()
#     main_group.append(game.group)
#     game.press()                 # start / jump / retry
#     game.tick(now, sfx)          # every loop
#
# Drawn into a single 1-bit Bitmap like the eyes, so no per-frame allocation.
# Physics are time-based rather than per-frame, so the feel doesn't change
# when the loop speeds up or slows down.

import time
import random
import displayio
import terminalio
from adafruit_display_text import label

from eyes import _fill as fill_rect

W, H = 128, 64
GROUND_Y = 52               # top of the ground line
DINO_X = 12
DINO_W, DINO_H = 10, 14

# Tuning. A 128px screen gives you very little reaction time, so this is
# deliberately gentler than the Chrome original: a floatier jump, slower
# start, a gentle ramp, and generous gaps between obstacles.
GRAVITY = 640.0             # px/s^2
JUMP_V = -200.0             # px/s, roughly a 31px apex over 0.63s
START_SPEED = 46.0          # px/s
MAX_SPEED = 104.0
RAMP = 0.032                # speed gained per point of score
JUMP_BUFFER = 0.22          # press slightly early and it still counts

TITLE, PLAYING, OVER = 0, 1, 2


class DinoGame:
    def __init__(self):
        self.bitmap = displayio.Bitmap(W, H, 2)
        palette = displayio.Palette(2)
        palette[0] = 0x000000
        palette[1] = 0xFFFFFF

        self.group = displayio.Group()
        self.group.append(displayio.TileGrid(self.bitmap, pixel_shader=palette))

        self.score_label = label.Label(terminalio.FONT, text="", scale=1, x=96, y=9)
        self.hi_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=9)
        self.line1 = label.Label(terminalio.FONT, text="", scale=1, x=0, y=22)
        self.line2 = label.Label(terminalio.FONT, text="", scale=1, x=0, y=34)
        for lbl in (self.score_label, self.hi_label, self.line1, self.line2):
            self.group.append(lbl)

        self.high = 0
        self.state = TITLE
        self._last = time.monotonic()
        self.reset(to_title=True)

    # ---------- helpers ----------

    @staticmethod
    def _centre(lbl, text):
        lbl.text = text
        lbl.x = max(0, (W - len(text) * 6) // 2)

    def reset(self, to_title=False):
        self.y = float(GROUND_Y - DINO_H)
        self.vy = 0.0
        self.on_ground = True
        self.obstacles = []
        self.score = 0.0
        self.speed = START_SPEED
        self.ground_offset = 0.0
        self.clouds = [[90.0, 12], [30.0, 20]]
        self.next_spawn = time.monotonic() + 2.2      # a runway before cactus 1
        self.buffered_jump = -10.0
        self._last_point_sound = 0
        self.state = TITLE if to_title else PLAYING
        self._sync_labels()

    def _sync_labels(self):
        title = self.state == TITLE
        over = self.state == OVER
        self.line1.hidden = not (title or over)
        self.line2.hidden = not (title or over)
        self.score_label.hidden = title
        self.hi_label.hidden = title

        if title:
            self._centre(self.line1, "Dinosaurrr rawr")
            self._centre(self.line2, "Press button to start")
        elif over:
            self._centre(self.line1, "GAME OVER")
            self._centre(self.line2, "Press to retry")

    # ---------- input ----------

    def press(self, sfx=None):
        """Button 2: start, jump, or retry depending on state."""
        if self.state == TITLE:
            self.reset()
            self.state = PLAYING
            self._sync_labels()
            if sfx:
                sfx.play("start")
        elif self.state == PLAYING:
            if self.on_ground:
                self._jump(sfx)
            else:
                # pressed a fraction too early -- remember it and fire on landing
                self.buffered_jump = time.monotonic()
        else:                                   # OVER
            self.reset()
            self.state = PLAYING
            self._sync_labels()
            if sfx:
                sfx.play("start")

    def _jump(self, sfx):
        self.vy = JUMP_V
        self.on_ground = False
        self.buffered_jump = -10.0
        if sfx:
            sfx.play("jump")

    # ---------- update ----------

    def tick(self, now=None, sfx=None):
        now = now or time.monotonic()
        dt = now - self._last
        self._last = now
        if dt > 0.05:                # a network stall shouldn't teleport things
            dt = 0.05

        if self.state == PLAYING:
            self._update(dt, now, sfx)

        self._draw()

    def _update(self, dt, now, sfx):
        # dino physics
        if not self.on_ground:
            self.vy += GRAVITY * dt
            self.y += self.vy * dt
            floor = float(GROUND_Y - DINO_H)
            if self.y >= floor:
                self.y = floor
                self.vy = 0.0
                self.on_ground = True
                if now - self.buffered_jump < JUMP_BUFFER:
                    self._jump(sfx)

        # world scroll, accelerating with score
        self.speed = min(MAX_SPEED, START_SPEED + self.score * RAMP)
        shift = self.speed * dt
        self.ground_offset = (self.ground_offset + shift) % 8

        for cloud in self.clouds:
            cloud[0] -= shift * 0.25
            if cloud[0] < -20:
                cloud[0] = W + random.uniform(5, 45)
                cloud[1] = random.randint(8, 24)

        for obstacle in self.obstacles:
            obstacle[0] -= shift
        self.obstacles = [o for o in self.obstacles if o[0] + o[1] > -2]

        # spawning -- gaps shrink as things speed up, but stay clearable
        if now >= self.next_spawn:
            tall = random.random() < 0.22
            width = 7 if tall else 5
            height = 14 if tall else 9
            self.obstacles.append([float(W + 4), width, height])
            gap = random.uniform(1.25, 2.3) * (START_SPEED / self.speed)
            self.next_spawn = now + max(0.85, gap)

        # score
        before = int(self.score)
        self.score += dt * 10.0
        after = int(self.score)
        if sfx and after // 100 > self._last_point_sound:
            self._last_point_sound = after // 100
            sfx.play("point")
        if after != before:
            self.score_label.text = f"{after:04d}"
            self.hi_label.text = f"HI {self.high:04d}"

        # collision, with two pixels of forgiveness on each side
        dino_left = DINO_X + 2
        dino_right = DINO_X + DINO_W - 2
        dino_bottom = self.y + DINO_H
        for x, width, height in self.obstacles:
            if x + width - 2 < dino_left or x + 2 > dino_right:
                continue
            if dino_bottom > GROUND_Y - height + 2:
                self._game_over(sfx)
                break

    def _game_over(self, sfx):
        self.state = OVER
        final = int(self.score)
        beat_record = final > self.high
        if beat_record:
            self.high = final
        self.hi_label.text = f"HI {self.high:04d}"
        self._sync_labels()
        if sfx:
            sfx.play("win" if beat_record else "fail")

    # ---------- drawing ----------

    def _draw(self):
        bmp = self.bitmap
        fill_rect(bmp, 0, 0, W, H, 0)

        # clouds
        for cx, cy in self.clouds:
            x = int(cx)
            fill_rect(bmp, x, cy, x + 11, cy + 2, 1)
            fill_rect(bmp, x + 3, cy - 2, x + 8, cy, 1)

        # ground: solid line plus scrolling specks so motion is legible
        fill_rect(bmp, 0, GROUND_Y, W, GROUND_Y + 1, 1)
        start = -int(self.ground_offset)
        for x in range(start, W, 8):
            fill_rect(bmp, x + 2, GROUND_Y + 3, x + 5, GROUND_Y + 4, 1)

        if self.state != TITLE:
            self._draw_dino(int(self.y))
            for x, width, height in self.obstacles:
                self._draw_cactus(int(x), width, height)
        else:
            self._draw_dino(GROUND_Y - DINO_H, still=True)

    def _draw_dino(self, y, still=False):
        bmp = self.bitmap
        x = DINO_X
        fill_rect(bmp, x + 4, y, x + 10, y + 5, 1)          # head
        fill_rect(bmp, x + 9, y + 3, x + 10, y + 5, 1)      # snout
        fill_rect(bmp, x + 8, y + 1, x + 9, y + 2, 0)       # eye
        fill_rect(bmp, x + 2, y + 5, x + 8, y + 10, 1)      # body
        fill_rect(bmp, x, y + 6, x + 3, y + 8, 1)           # tail

        # legs alternate with the ground scroll while running
        if still or not self.on_ground:
            fill_rect(bmp, x + 3, y + 10, x + 5, y + 14, 1)
            fill_rect(bmp, x + 6, y + 10, x + 8, y + 14, 1)
        elif int(self.ground_offset) % 8 < 4:
            fill_rect(bmp, x + 3, y + 10, x + 5, y + 14, 1)
            fill_rect(bmp, x + 6, y + 10, x + 8, y + 12, 1)
        else:
            fill_rect(bmp, x + 3, y + 10, x + 5, y + 12, 1)
            fill_rect(bmp, x + 6, y + 10, x + 8, y + 14, 1)

    def _draw_cactus(self, x, width, height):
        bmp = self.bitmap
        top = GROUND_Y - height
        fill_rect(bmp, x + width // 3, top, x + width - width // 3, GROUND_Y, 1)
        arm = top + height // 3
        fill_rect(bmp, x, arm, x + width // 3, arm + 2, 1)
        fill_rect(bmp, x, arm - 3, x + 2, arm + 2, 1)
        fill_rect(bmp, x + width - width // 3, arm + 3, x + width, arm + 5, 1)
        fill_rect(bmp, x + width - 2, arm, x + width, arm + 5, 1)
