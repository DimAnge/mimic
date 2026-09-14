# Changelog

All notable changes to Mimic. Dates are the day the change landed on the board.

## Unreleased

### Added
- Spotify tab: playback state over the Spotify Web API with PKCE OAuth, play/pause
  on tap and skip on hold
- Calendar meeting popup, fed by a private iCal URL parsed on the bridge
- Buzzer soundboard of chiptune jingles
- Tab dots along the bottom of every screen
- Games menu holding the dino runner and a magic eight ball, both imported lazily
- Calendar tab showing the next few events, alongside the existing popup
- A date overlay on the face

### Changed
- Bridge now runs as a systemd user service so it starts at login
- Weather tab carries the large clock; the separate clock tab was removed
- Case at v6: breadboard pocket widened to 85x57 mm, button disc slot widened to
  22x16 mm to clear Dupont connectors, screen holder removed pending a top mount

### Removed
- `IDLE_SLEEP`: blanking the screen while someone is sitting at the desk made it
  a dark rectangle rather than a desk buddy
- Gene lookup tab
- Gmail notifications

## 0.1.0

### Added
- First working build: animated face, weather, system stats, timer and usage
- Non-blocking audio via a tone queue
- Edge-detected button handling with timestamp lockouts, no sleep-based debounce
- Burn-in protection: pixel shift plus night and idle dimming
