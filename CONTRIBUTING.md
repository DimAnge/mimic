# Contributing

Mimic is a personal desk project, so the bar is low and the scope is small.
Issues and pull requests are welcome anyway, especially these:

- You built one and something in the instructions was wrong or missing.
- Your OLED, buttons or buzzer are wired differently and the code needed changing.
- A screen that does something useful in one glance and fits in 128x64 pixels.

## Before opening a pull request

1. Deploy the board files and watch a full boot on `tio /dev/ttyACM0` with no
   tracebacks:

   ```bash
   cp code.py eyes.py dino.py eightball.py sfx.py icons.py \
      /media/$USER/CIRCUITPY/ && sync
   ```

2. If you touched the bridge, restart it — editing the file leaves the old
   process running: `systemctl --user restart mimic-bridge`.
3. Keep the two-button rule: everything reachable with tap, hold, and nothing else.

## Style

- CircuitPython, standard library plus the Adafruit display stack. The bridge is
  standard library only, so it runs anywhere with Python and no pip install.
- No blocking calls in the main loop. No `time.sleep()` for debouncing.
- The screen is monochrome. If an idea needs colour to work, it does not work.
- Comments explain why, not what.

## Adding a screen

Screens are self-contained draw functions plus an entry in the tab list. A new
screen should:

- render in a single frame with no network call on the draw path
- be imported lazily if it is large, the way the two games are
- degrade to something readable when the bridge is unreachable
- use at most one button action, on Button 2

## Reporting a build problem

Include your CircuitPython version, the boot output from the serial console, and
a photo of the wiring. Most build problems are a seated connector or a 5 GHz
network.
