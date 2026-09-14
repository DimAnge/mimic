# Hardware

## Breadboard layout

The reference build sits on a half-size breadboard with the top rail strip
trimmed off so it drops into the case tray.

| Component | Connection | Breadboard hole |
| --- | --- | --- |
| OLED | `SDA` -> `GP0`, pin 1 | 1a |
| OLED | `SCL` -> `GP1`, pin 2 | 2a |
| OLED | `GND`, pin 38 | 3j |
| OLED | `VCC` -> `3V3`, pin 36 | 5j |
| Button 1 | leg A -> `GP2`, pin 4 | 4a |
| Button 1 | leg B -> `GND`, pin 3 | 3a |
| Button 2 | leg A -> `GP3`, pin 5 | 5a |
| Button 2 | leg B -> `GND`, pin 8 | 8a |
| Buzzer | `SIG` -> `GP15`, pin 20 | 20a |
| Buzzer | `VCC` -> `VBUS`, 5V, pin 40 | 1j |
| Buzzer | `GND`, pin 18 | 18a |

Row *n* on the `a` side of the channel is physical pin *n*; row *n* on the `j`
side is pin *41 − n*. That is the whole trick to reading this table against the
board.

Wire colours used in the diagrams: red for 3V3, dark grey for ground, blue for
I2C data, yellow for I2C clock, green for button inputs, purple for the buzzer
signal.

## Checking the wiring

Check every connection against the table above:

- after wiring, before loading `code.py`
- after any work on the case
- after anything involving glue

## Printed parts

| Part | Source |
| --- | --- |
| `tray.stl` | Custom, `case.scad` |
| `lid.stl` | Custom, `case.scad` |
| `spacer.stl` | Custom, `case.scad` |
| Screen stand | [Minimalist OLED 0.96" modular case](https://makerworld.com/en/models/2085334-minimalist-oled-0-96-modern-modular-cases#profileId-2253779) by Maker Engineer |
| Button assemblies | [Push button assembly](https://makerworld.com/en/models/1791039-push-button-assembly?from=search#profileId-1908757) by Leroyd |

Check the licence on each MakerWorld model before reusing it, and say so here if
you remixed rather than printed as-is.

`case.scad` builds the three custom parts. Set the `part` variable and export:

```bash
openscad -D 'part="tray"'   -o stl/tray.stl   case.scad
openscad -D 'part="lid"'    -o stl/lid.stl    case.scad
openscad -D 'part="spacer"' -o stl/spacer.stl case.scad
```

Print settings: 0.2 mm layers, 15% infill, PLA, no supports. The tray prints
open-side up. Print the two MakerWorld parts first — they are quick, and they
tell you whether your printer is holding tolerance before you commit hours to
the tray.

### Known dimensions (v6)

| Feature | Value |
| --- | --- |
| Breadboard pocket | 85 x 57 mm |
| Button counterbore | 25.39 mm |
| Button disc slot | 22 x 16 mm (clears Dupont connectors) |
| USB opening | right wall |
| Lid | locating lip plus cable pass-through slot |
| Spacer | sets the stack height inside the tray |

### Assembly warning

Do not glue Dupont connectors. Superglue wicks between the metal contacts and
insulates them; the joint looks perfect and conducts nothing. The pinched barrel
grip is enough on its own. If a button has gone dead after assembly, wiggle the
connector to crack any glue and re-seat it dry.
