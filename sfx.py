# sfx.py -- non-blocking buzzer soundboard for a passive piezo
#
#     from sfx import Sfx
#     sfx = Sfx(board.GP15)
#     sfx.play("boot")
#     while True:
#         sfx.tick()          # call every loop; never blocks
#
# A passive buzzer can hit arbitrary frequencies, so short chiptune-style
# motifs work well. Full tunes don't -- there's no polyphony and no envelope.

import time
import pwmio

# Frequencies in Hz. Rests are freq 0.
MELODIES = {
    # --- UI ---
    "boot":     ((523, 0.07), (659, 0.07), (784, 0.07), (1047, 0.14)),
    "tab":      ((2000, 0.04),),
    "select":   ((1000, 0.05),),
    "home":     ((700, 0.05), (500, 0.10)),
    "back":     ((500, 0.06),),

    # --- Tasks / timers ---
    "task":     ((880, 0.06), (1319, 0.13)),
    "alarm":    ((1319, 0.13), (0, 0.06), (1319, 0.13), (0, 0.06),
                 (1568, 0.13), (0, 0.06), (1319, 0.26)),

    # --- Claude usage ---
    "alert":    ((1568, 0.08), (0, 0.05), (1568, 0.08), (0, 0.05),
                 (1568, 0.18)),
    "reset":    ((784, 0.06), (988, 0.06), (1319, 0.16)),

    # --- Dino game ---
    "jump":     ((1400, 0.025),),
    "duck":     ((900, 0.025),),
    "point":    ((1760, 0.03),),
    "fail":     ((523, 0.10), (494, 0.10), (392, 0.10), (262, 0.26)),
    "win":      ((659, 0.06), (784, 0.06), (988, 0.06), (1319, 0.18)),
    "start":    ((392, 0.06), (523, 0.06), (659, 0.12)),
}

QUIET = 1500        # UI feedback -- barely audible across a desk
LOUD = 8000         # alarms and failures


class Sfx:
    def __init__(self, pin, quiet=QUIET, loud=LOUD):
        self.pwm = pwmio.PWMOut(pin, variable_frequency=True)
        self.pwm.duty_cycle = 0
        self.quiet = quiet
        self.loud = loud
        self.muted = False
        self._queue = []
        self._until = 0.0
        self._busy = False

    # ---------- queueing ----------

    def tone(self, freq, seconds, duty=None):
        """Queue a single note. freq 0 is a rest."""
        if self.muted:
            return
        self._queue.append((freq, seconds, self.quiet if duty is None else duty))

    def play(self, name, duty=None):
        """Queue a named melody from MELODIES."""
        if self.muted:
            return
        melody = MELODIES.get(name)
        if not melody:
            return
        volume = duty if duty is not None else (
            self.loud if name in ("alarm", "fail", "alert") else self.quiet)
        for freq, seconds in melody:
            self._queue.append((freq, seconds, volume))

    def stop(self):
        """Silence immediately and drop anything pending."""
        self._queue = []
        self._busy = False
        self._until = 0.0
        self.pwm.duty_cycle = 0

    @property
    def busy(self):
        return self._busy or bool(self._queue)

    # ---------- per-loop update ----------

    def tick(self, now=None):
        now = now or time.monotonic()
        if self._busy and now >= self._until:
            self.pwm.duty_cycle = 0
            self._busy = False
        if not self._busy and self._queue and now >= self._until:
            freq, seconds, duty = self._queue.pop(0)
            if freq > 0 and duty > 0:
                self.pwm.frequency = int(freq)
                self.pwm.duty_cycle = duty
            self._until = now + seconds
            self._busy = True
