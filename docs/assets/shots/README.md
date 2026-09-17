# Screen captures

Real frames, not mockups.

**Captured over USB.** `screenshot.py` on the Pico walks `display.root_group`,
redraws it into a 1-bit buffer and prints it as hex; `tools/shot.py` on the PC
turns that back into a PNG.

```bash
tio /dev/ttyACM0                 # walk the tabs, press "s" once per screen
cat > /tmp/dumps.txt             # paste the console output, then Ctrl-D
python3 tools/shot.py --paste /tmp/dumps.txt --bezel \
  --names face,calendar,spotify,system,dino,eightball
```

**Recovered from photographs.** `weather.png`, `usage.png` and `games.png` come
from close-up photos instead: `tools/make_photos.py` finds the glass in the
photo, squares it to 128 x 64, thresholds it back to two colours and drops the
dust specks.

```bash
python3 tools/make_photos.py /path/to/photos
```

Then rebuild the contact sheet used in the README:

```bash
python3 tools/make_sheet.py --cols=3 \
  FACE=docs/assets/shots/face.png WEATHER=docs/assets/shots/weather.png \
  CALENDAR=docs/assets/shots/calendar.png SPOTIFY=docs/assets/shots/spotify.png \
  SYSTEM=docs/assets/shots/system.png USAGE=docs/assets/shots/usage.png \
  GAMES=docs/assets/shots/games.png DINO=docs/assets/shots/dino.png \
  "8 BALL=docs/assets/shots/eightball.png"
```

Still missing: the timer screen.
