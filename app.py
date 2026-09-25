import board, busio, displayio, terminalio, os, time, wifi, rtc, digitalio, random
import supervisor
import microcontroller
from adafruit_display_text import label
import adafruit_displayio_ssd1306
import i2cdisplaybus
import adafruit_connection_manager
import adafruit_requests

# A cold power-up and a soft reload are very different starts. On a reload
# (saving a file, Ctrl-D in tio) the OLED is already powered and the WiFi
# radio is already warm. On a cold boot everything wakes at the same instant,
# and CircuitPython starts running this file within milliseconds -- before
# the OLED is ready to answer on I2C. Give the hardware a beat first.
COLD_BOOT = supervisor.runtime.run_reason == supervisor.RunReason.STARTUP
if COLD_BOOT:
    time.sleep(1.0)

from eyes import Eyes, _fill as fill_rect
from sfx import Sfx
from icons import draw_weather, SIZE as ICON_SIZE

# dino.py and eightball.py are imported on first use instead of here.
# CircuitPython compiles every .py at import time, and those two are the
# largest modules in the project -- deferring them cuts seconds off boot.
BOOT_T0 = time.monotonic()


def boot_mark(label_text):
    print(f"[boot {time.monotonic() - BOOT_T0:5.2f}s] {label_text}")

# --- 1. CONFIG ---
CITY = "Athens,GR"
UNITS = "metric"

# Put BRIDGE_URL in settings.toml so swapping PCs doesn't mean editing code:
#     BRIDGE_URL = "http://192.168.1.42:8080/status"
# Find the IP with:  hostname -I | awk '{print $1}'
BRIDGE_URL = os.getenv("BRIDGE_URL") or "http://192.168.1.100:8080/status"
BRIDGE_BASE = BRIDGE_URL.rsplit("/", 1)[0]      # drop "/status"

MODES = ["FACE", "WEATHER", "CALENDAR", "SPOTIFY", "SYSTEM", "TIMER",
         "USAGE", "GAMES"]

GAMES = ("Dino Run", "Magic 8-Ball")

MEETING_WARN_MIN = 15        # popup appears this many minutes ahead
UPTIME_TIRED_MIN = 2 * 24 * 60   # PC up this long and the eyes go droopy
USAGE_ALERT_PCT = 90         # usage this high and the eyes look alarmed

WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def weekday_name(year, month, day):
    """Sakamoto's algorithm -- the RTC doesn't fill in tm_wday for us."""
    table = (0, 3, 2, 5, 0, 3, 5, 1, 4, 6, 2, 4)
    y = year - 1 if month < 3 else year
    idx = (y + y // 4 - y // 100 + y // 400 + table[month - 1] + day) % 7
    return WEEKDAYS[idx]


# --- 2. HARDWARE SETUP ---
btn_mode = digitalio.DigitalInOut(board.GP2)
btn_mode.direction = digitalio.Direction.INPUT
btn_mode.pull = digitalio.Pull.UP

btn_action = digitalio.DigitalInOut(board.GP3)
btn_action.direction = digitalio.Direction.INPUT
btn_action.pull = digitalio.Pull.UP

sfx = Sfx(board.GP15)

def init_display(attempts=6):
    """Bring up the OLED, retrying while it finishes powering on.

    The classic cold-boot failure is busio.I2C raising 'No pull up found on
    SDA or SCL': the display's pull-ups aren't live yet, so the bus looks
    unconnected. Half a second later it's fine.
    """
    for i in range(attempts):
        displayio.release_displays()
        bus = None
        try:
            bus = busio.I2C(board.GP1, board.GP0, frequency=400_000)
            dbus = i2cdisplaybus.I2CDisplayBus(bus, device_address=0x3c)
            return adafruit_displayio_ssd1306.SSD1306(dbus, width=128, height=64)
        except Exception as exc:
            print(f"Display init attempt {i + 1} failed:", exc)
            if bus is not None:
                try:
                    bus.deinit()
                except Exception:
                    pass
            time.sleep(0.5)
    raise RuntimeError("OLED never came up -- check wiring")


display = init_display()
display.auto_refresh = False

main_group = displayio.Group()
display.root_group = main_group

mono = displayio.Palette(2)
mono[0] = 0x000000
mono[1] = 0xFFFFFF


def new_bitmap(width, height):
    return displayio.Bitmap(width, height, 2)


def draw_bar(bitmap, pct):
    """Hollow rectangle with a solid fill proportional to pct (0-100)."""
    w, h = bitmap.width, bitmap.height
    fill_rect(bitmap, 0, 0, w, h, 0)
    fill_rect(bitmap, 0, 0, w, 1, 1)
    fill_rect(bitmap, 0, h - 1, w, h, 1)
    fill_rect(bitmap, 0, 0, 1, h, 1)
    fill_rect(bitmap, w - 1, 0, w, h, 1)
    if pct < 0:
        pct = 0
    elif pct > 100:
        pct = 100
    filled = ((w - 4) * pct) // 100
    if filled > 0:
        fill_rect(bitmap, 2, 2, 2 + filled, h - 2, 1)


def fit(text, chars=21):
    return text[:chars]


# --- Screen: the face ---
eyes = Eyes()
face_time_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=6)
face_pct_label = label.Label(terminalio.FONT, text="", scale=1, x=100, y=6)
face_date_label = label.Label(terminalio.FONT, text="", scale=1, x=34, y=58)

# small note glyph, shown in the corner whenever music is playing
note_bitmap = new_bitmap(6, 8)
fill_rect(note_bitmap, 4, 0, 6, 5, 1)        # stem
fill_rect(note_bitmap, 0, 4, 5, 8, 1)        # head
fill_rect(note_bitmap, 1, 5, 4, 7, 0)        # hollow it out
face_note = displayio.TileGrid(note_bitmap, pixel_shader=mono, x=38, y=1)
face_note.hidden = True

face_group = displayio.Group()
face_group.append(eyes.group)
face_group.append(face_time_label)
face_group.append(face_pct_label)
face_group.append(face_date_label)
face_group.append(face_note)
main_group.append(face_group)

# --- Screen: two lines of text (timer) ---
text_group = displayio.Group()
time_label = label.Label(terminalio.FONT, text="Booting...", scale=2, x=16, y=22)
date_label = label.Label(terminalio.FONT, text="Please Wait", scale=1, x=16, y=50)
text_group.append(time_label)
text_group.append(date_label)
main_group.append(text_group)

# --- Screen: weather ---
icon_bitmap = new_bitmap(ICON_SIZE, ICON_SIZE)
weather_group = displayio.Group()
wx_time_label = label.Label(terminalio.FONT, text="--:--", scale=3, x=2, y=22)
wx_temp_label = label.Label(terminalio.FONT, text="--.-C", scale=2, x=2, y=46)
wx_desc_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=58)
weather_group.append(displayio.TileGrid(icon_bitmap, pixel_shader=mono, x=96, y=8))
weather_group.append(wx_time_label)
weather_group.append(wx_temp_label)
weather_group.append(wx_desc_label)
main_group.append(weather_group)

# --- Screen: Spotify ---
sp_bar = new_bitmap(124, 6)
spotify_group = displayio.Group()
sp_track_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=13)
sp_artist_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=25)
sp_state_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=46)
sp_hint_label = label.Label(terminalio.FONT, text="tap play  hold next",
                            scale=1, x=2, y=57)
spotify_group.append(displayio.TileGrid(sp_bar, pixel_shader=mono, x=2, y=32))
spotify_group.append(sp_track_label)
spotify_group.append(sp_artist_label)
spotify_group.append(sp_state_label)
spotify_group.append(sp_hint_label)
main_group.append(spotify_group)

# --- Screen: upcoming calendar events ---
calendar_group = displayio.Group()
cal_index_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=11)
cal_when_label = label.Label(terminalio.FONT, text="", scale=1, x=60, y=11)
cal_line1_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=28)
cal_line2_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=40)
cal_in_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=56)
calendar_group.append(cal_index_label)
calendar_group.append(cal_when_label)
calendar_group.append(cal_line1_label)
calendar_group.append(cal_line2_label)
calendar_group.append(cal_in_label)
main_group.append(calendar_group)

# --- Screen: Claude usage ---
usage_bar = new_bitmap(124, 12)
usage_group = displayio.Group()
usage_pct_label = label.Label(terminalio.FONT, text="--%", scale=2, x=4, y=18)
usage_scope_label = label.Label(terminalio.FONT, text="SESSION", scale=1, x=62, y=12)
usage_reset_label = label.Label(terminalio.FONT, text="--", scale=1, x=62, y=24)
usage_week_label = label.Label(terminalio.FONT, text="", scale=1, x=4, y=56)
usage_group.append(displayio.TileGrid(usage_bar, pixel_shader=mono, x=2, y=36))
usage_group.append(usage_pct_label)
usage_group.append(usage_scope_label)
usage_group.append(usage_reset_label)
usage_group.append(usage_week_label)
main_group.append(usage_group)

# --- Screen: PC system stats ---
cpu_bar = new_bitmap(124, 8)
ram_bar = new_bitmap(124, 8)
system_group = displayio.Group()
cpu_label = label.Label(terminalio.FONT, text="CPU --%", scale=1, x=2, y=10)
temp_label = label.Label(terminalio.FONT, text="", scale=1, x=90, y=10)
ram_label = label.Label(terminalio.FONT, text="RAM --%", scale=1, x=2, y=32)
ram_detail_label = label.Label(terminalio.FONT, text="", scale=1, x=62, y=32)
sys_foot_label = label.Label(terminalio.FONT, text="", scale=1, x=2, y=57)
system_group.append(displayio.TileGrid(cpu_bar, pixel_shader=mono, x=2, y=16))
system_group.append(displayio.TileGrid(ram_bar, pixel_shader=mono, x=2, y=38))
system_group.append(cpu_label)
system_group.append(temp_label)
system_group.append(ram_label)
system_group.append(ram_detail_label)
system_group.append(sys_foot_label)
main_group.append(system_group)

# --- Screen: the games menu, and the games themselves ---
# Both games are built the first time you open them. Each carries its own
# 128x64 bitmap and a pile of labels, and most sessions never touch them.
game = None
ball = None
DINO_PLAYING = 1              # filled in properly when dino.py loads


def ensure_dino():
    global game, DINO_PLAYING
    if game is None:
        from dino import DinoGame, PLAYING
        DINO_PLAYING = PLAYING
        game = DinoGame()
        main_group.append(game.group)
    return game


def ensure_ball():
    global ball
    if ball is None:
        from eightball import EightBall
        ball = EightBall()
        main_group.append(ball.group)
    return ball


games_group = displayio.Group()
games_title = label.Label(terminalio.FONT, text="GAMES", scale=2, x=34, y=14)
games_items = [
    label.Label(terminalio.FONT, text="", scale=1, x=8, y=32),
    label.Label(terminalio.FONT, text="", scale=1, x=8, y=44),
]
games_hint = label.Label(terminalio.FONT, text="tap pick  hold start",
                         scale=1, x=4, y=58)
games_group.append(games_title)
for lbl in games_items:
    games_group.append(lbl)
games_group.append(games_hint)
main_group.append(games_group)

game_index = 0
games_state = "menu"          # "menu" | "dino" | "eightball"


def render_games_menu():
    for i, lbl in enumerate(games_items):
        if i < len(GAMES):
            lbl.text = ("> " if i == game_index else "  ") + GAMES[i]
        else:
            lbl.text = ""

# --- Overlay: tab indicator dots ---
DOT_SLOT = 8
dots_bitmap = new_bitmap(len(MODES) * DOT_SLOT, 4)
dots_tile = displayio.TileGrid(dots_bitmap, pixel_shader=mono,
                               x=(128 - len(MODES) * DOT_SLOT) // 2, y=0)
main_group.append(dots_tile)


def draw_dots(active):
    fill_rect(dots_bitmap, 0, 0, dots_bitmap.width, 4, 0)
    for i in range(len(MODES)):
        cx = i * DOT_SLOT + DOT_SLOT // 2
        if i == active:
            fill_rect(dots_bitmap, cx - 3, 0, cx + 3, 3, 1)
        else:
            fill_rect(dots_bitmap, cx - 1, 1, cx + 1, 3, 1)


# --- Overlay: meeting popup, sits above everything including the dots ---
POPUP_W, POPUP_H = 120, 44
popup_bitmap = new_bitmap(POPUP_W, POPUP_H)
fill_rect(popup_bitmap, 0, 0, POPUP_W, POPUP_H, 1)          # white border
fill_rect(popup_bitmap, 2, 2, POPUP_W - 2, POPUP_H - 2, 0)  # black inside
popup_group = displayio.Group()
popup_title = label.Label(terminalio.FONT, text="", scale=1, x=0, y=26)
popup_when = label.Label(terminalio.FONT, text="", scale=2, x=0, y=41)
popup_hint = label.Label(terminalio.FONT, text="", scale=1, x=0, y=54)
popup_group.append(displayio.TileGrid(popup_bitmap, pixel_shader=mono, x=4, y=10))
popup_group.append(popup_title)
popup_group.append(popup_when)
popup_group.append(popup_hint)
main_group.append(popup_group)
popup_group.hidden = True


def centre(lbl, text, char_w=6):
    lbl.text = text
    lbl.x = max(0, (128 - len(text) * char_w) // 2)


def set_lines(big, small):
    time_label.text = big
    time_label.x = max(0, (128 - len(big) * 12) // 2)
    date_label.text = small
    date_label.x = max(0, (128 - len(small) * 6) // 2)


def show_screen(which):
    face_group.hidden = which != "face"
    text_group.hidden = which != "text"
    weather_group.hidden = which != "weather"
    calendar_group.hidden = which != "calendar"
    spotify_group.hidden = which != "spotify"
    usage_group.hidden = which != "usage"
    system_group.hidden = which != "system"
    games_group.hidden = which != "games"
    if game is not None:
        game.group.hidden = which != "dino"
    if ball is not None:
        ball.group.hidden = which != "eightball"
    # a game wants the whole panel; the menu is happy to share
    dots_tile.hidden = which in ("dino", "eightball")


show_screen("text")
draw_dots(0)
boot_mark("screens built")


# --- 3. NETWORK ---
ssid = os.getenv("WIFI_SSID")
password = os.getenv("WIFI_PASSWORD")
api_key = os.getenv("OPENWEATHER_TOKEN")

pool = None
ssl_context = None
requests = None


def online():
    try:
        return bool(wifi.radio.connected)
    except AttributeError:
        # older builds lack .connected; an address means we're associated
        return wifi.radio.ipv4_address is not None
    except Exception:
        return False


def wait_for_ip(timeout=6.0):
    """Association and having an address are two different moments.

    On a cold boot connect() can return before DHCP has finished, and any
    socket opened in that window fails. A soft reload never hits this,
    because the address survives from the previous run.
    """
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        try:
            if wifi.radio.ipv4_address is not None:
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


def connect_wifi(attempts=5, show=True):
    """Try to associate, a few times.

    A cold power-up is slower than a soft reload: the radio firmware has to
    load and associate from scratch, and the first attempt often fails.
    During development you almost never see this, because saving a file
    triggers a soft reload that keeps WiFi up from the previous run.
    """
    for i in range(attempts):
        if show:
            set_lines("Wi-Fi", f"Connecting {i + 1}/{attempts}")
            display.refresh()
        try:
            wifi.radio.connect(ssid, password)
            if online() and wait_for_ip():
                print("Wi-Fi up, address", wifi.radio.ipv4_address)
                return True
        except Exception as exc:
            print(f"Wi-Fi attempt {i + 1} failed:", exc)
        if i + 1 < attempts:
            time.sleep(1.5)
    return False


def rebuild_session():
    """Fresh socket pool and session after WiFi comes back.

    Sockets opened before a drop are dead, but the pool doesn't know that.
    Without this, the first requests after reconnecting fail like the
    bridge is still unreachable.
    """
    global pool, ssl_context, requests
    try:
        adafruit_connection_manager.connection_manager_close_all(release_references=True)
    except Exception:
        pass
    pool = adafruit_connection_manager.get_radio_socketpool(wifi.radio)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(wifi.radio)
    requests = adafruit_requests.Session(pool, ssl_context)


print("Connecting Wi-Fi...")
if connect_wifi(attempts=8 if COLD_BOOT else 5):
    boot_mark("wifi connected")
else:
    boot_mark("wifi FAILED -- continuing offline")
rebuild_session()
time.sleep(0.3)          # let the radio finish settling before the first socket


# --- Burn-in protection ---
SHIFT_OFFSETS = ((0, 0), (1, 0), (2, 1), (1, 2), (0, 1))
shift_index = 0
next_shift = 0.0
SHIFT_INTERVAL = 180.0

current_brightness = None


def set_brightness(value):
    global current_brightness
    if value == current_brightness:
        return
    try:
        display.brightness = value
        current_brightness = value
    except Exception:
        current_brightness = value


# --- 4. DATA FETCHING ---
time_synced = False
last_time_sync = -999.0
TIME_RESYNC = 6 * 3600.0


def apply_clock(parts, now):
    """Set the RTC from a [Y, M, D, h, m, s] list."""
    global time_synced, last_time_sync
    try:
        rtc.RTC().datetime = time.struct_time(
            (parts[0], parts[1], parts[2],
             parts[3], parts[4], parts[5], 0, 0, -1))
        time_synced = True
        last_time_sync = now
        return True
    except Exception as exc:
        print("Clock set failed:", exc)
        return False


def get_time_https():
    """Fallback only. A TLS handshake here costs several seconds at boot."""
    print("Syncing time over HTTPS...")
    r = None
    try:
        url = "https://timeapi.io/api/Time/current/zone?timeZone=Europe/Athens"
        r = requests.get(url)
        d = r.json()
        return apply_clock([d["year"], d["month"], d["day"],
                            d["hour"], d["minute"], d["seconds"]],
                           time.monotonic())
    except Exception as e:
        print("Time Error:", e)
        return False
    finally:
        if r is not None:
            try:
                r.close()
            except Exception:
                pass


weather_temp = "--.-C"
weather_desc = "no data yet"
weather_icon = ""
weather_mood = "neutral"
last_weather_fetch = -999.0
WEATHER_REFRESH = 600.0


def fetch_weather(now):
    global weather_temp, weather_desc, weather_icon, weather_mood
    global last_weather_fetch
    last_weather_fetch = now
    r = None
    try:
        url = (f"http://api.openweathermap.org/data/2.5/weather"
               f"?q={CITY}&appid={api_key}&units={UNITS}")
        r = requests.get(url)
        d = r.json()
    except Exception:
        weather_temp, weather_desc, weather_icon = "Net Err", "retry later", ""
        return
    finally:
        if r is not None:
            try:
                r.close()
            except Exception:
                pass

    if "main" not in d:
        weather_temp, weather_desc, weather_icon = "Key Err", "check token", ""
        return

    weather_temp = f"{d['main']['temp']:.1f}C"
    entry = d["weather"][0]
    weather_desc = entry.get("description", "")[:21]
    weather_icon = entry.get("icon", "")

    # Recorded rather than applied: context_mood() decides what actually wins.
    low = weather_desc.lower()
    if "rain" in low or "storm" in low or "snow" in low:
        weather_mood = "sad"
    elif "clear" in low:
        weather_mood = "happy"
    else:
        weather_mood = "neutral"


def render_weather():
    t = time.localtime()
    wx_time_label.text = f"{t.tm_hour:02d}:{t.tm_min:02d}"
    wx_temp_label.text = weather_temp
    wx_desc_label.text = weather_desc
    draw_weather(icon_bitmap, weather_icon)


# --- Everything from the PC bridge, in one request ---
status_ok = False
usage_ok = False
usage_session_pct = 0
usage_session_reset = "--"
usage_week_pct = 0
usage_week_reset = "--"
usage_alerted = False
sys_cpu = 0
sys_ram = 0
sys_ram_used = 0.0
sys_ram_total = 0.0
sys_temp = None
sys_disk = 0
sys_uptime = "?"
sys_uptime_min = 0
sp_ok = False
sp_active = False
sp_playing = False
sp_track = ""
sp_artist = ""
sp_progress = 0
cal_ok = False
event_title = ""
event_in = None
event_at = ""
events = []
cal_index = 0
last_status_fetch = -999.0
bridge_failures = 0


last_net_error = ""          # shown on the system tab when the bridge is down


class NetworkStuck(Exception):
    """Raised when the network stack is provably dead; code.py soft-resets."""


# A soft reset is the only thing that clears the dead-stack state, and it only
# works once the network is actually ready -- which on a cold boot can take a
# minute or two. So we allow several, counted in non-volatile memory because
# ordinary variables don't survive a reset. code.py zeroes it on power-on.
STUCK_RESTART_LIMIT = 10


def _stuck_count():
    try:
        value = microcontroller.nvm[0]
        return value if value <= STUCK_RESTART_LIMIT else 0   # fresh flash reads 255
    except Exception:
        return 0


def _set_stuck_count(value):
    try:
        if microcontroller.nvm[0] != value:     # avoid needless flash writes
            microcontroller.nvm[0] = value
    except Exception:
        pass


def dns_works():
    """Can we resolve a public name? If not, nothing is getting through."""
    try:
        pool.getaddrinfo("api.openweathermap.org", 80)
        return True
    except Exception:
        return False


def network_stuck_restart():
    """Bridge dead AND DNS dead while WiFi claims to be up.

    That's not the bridge being off -- that's the Pico's network stack wedged,
    which happens when it talks too early after a cold boot. A soft reset
    clears it. Bounded, so a genuinely broken network can't reset forever.
    """
    count = _stuck_count()
    if count >= STUCK_RESTART_LIMIT:
        print(f"Network still dead after {count} restarts -- no more restarts")
        return
    _set_stuck_count(count + 1)
    print(f"Network stack stuck -- soft reset {count + 1}/{STUCK_RESTART_LIMIT}")
    set_lines("Network", f"reset {count + 1}/{STUCK_RESTART_LIMIT}")
    display.refresh()
    time.sleep(2.0)                     # give the network a little longer
    raise NetworkStuck()


def bridge_get(url, attempts=2):
    """GET with a retry, releasing the socket whatever happens.

    Short timeout on purpose: a dead stack makes every attempt hang for the
    full timeout, and a long one turned a stuck boot into 100 seconds of
    staring at "Waiting 5/5".

    The finally matters more than the retry: the connection pool is small,
    and a response that is never closed is a socket that never comes back.
    """
    global last_net_error
    for attempt in range(attempts):
        r = None
        try:
            r = requests.get(url, timeout=3)
            data = r.json()
            last_net_error = ""
            return data
        except Exception as exc:
            if attempt + 1 < attempts:
                time.sleep(0.4)
            else:
                last_net_error = str(exc) or type(exc).__name__
                print("Bridge fetch failed:", last_net_error)
        finally:
            if r is not None:
                try:
                    r.close()
                except Exception:
                    pass
    return None


def fetch_status(now):
    """One GET gets usage, PC stats, calendar and Spotify."""
    global status_ok, usage_ok, last_status_fetch, usage_alerted
    global usage_session_pct, usage_session_reset
    global usage_week_pct, usage_week_reset
    global sys_cpu, sys_ram, sys_ram_used, sys_ram_total
    global sys_temp, sys_disk, sys_uptime, sys_uptime_min
    global sp_ok, sp_active, sp_playing, sp_track, sp_artist, sp_progress
    global cal_ok, event_title, event_in, event_at, events, cal_index
    global time_synced, last_time_sync, bridge_failures

    last_status_fetch = now
    if not online():
        status_ok = False
        usage_ok = False
        face_pct_label.text = ""
        return

    d = bridge_get(BRIDGE_URL)
    if d is None:
        status_ok = False
        usage_ok = False
        face_pct_label.text = ""
        # Two failures in a row: is it just the bridge (PC off), or is the
        # whole stack dead? DNS tells them apart. Rebuilding the session was
        # tried here before and proven not to help -- only a reset does.
        bridge_failures += 1
        if bridge_failures >= 2:
            bridge_failures = 0
            if not dns_works():
                network_stuck_restart()
        return

    bridge_failures = 0
    _set_stuck_count(0)             # healthy again: re-arm the restart budget
    status_ok = True
    clock = d.get("clock")
    if clock and len(clock) >= 6:
        if not time_synced or now - last_time_sync > TIME_RESYNC:
            apply_clock(clock, now)

    sys_cpu = int(d.get("cpu_pct") or 0)
    sys_ram = int(d.get("ram_pct") or 0)
    sys_ram_used = d.get("ram_used_gb") or 0.0
    sys_ram_total = d.get("ram_total_gb") or 0.0
    sys_temp = d.get("temp_c")
    sys_disk = int(d.get("disk_pct") or 0)
    sys_uptime = str(d.get("uptime") or "?")
    sys_uptime_min = int(d.get("uptime_min") or 0)

    sp_ok = bool(d.get("sp_ok"))
    sp_active = bool(d.get("sp_active"))
    sp_playing = bool(d.get("sp_playing"))
    sp_track = str(d.get("sp_track") or "")
    sp_artist = str(d.get("sp_artist") or "")
    sp_progress = int(d.get("sp_progress") or 0)
    face_note.hidden = not sp_playing

    cal_ok = bool(d.get("cal_ok"))
    event_title = str(d.get("event_title") or "")
    event_in = d.get("event_in")
    event_at = str(d.get("event_at") or "")
    events = d.get("events") or []
    if cal_index >= len(events):
        cal_index = 0

    usage_ok = bool(d.get("usage_ok"))
    if usage_ok:
        previous = usage_session_pct
        usage_session_pct = int(d.get("session_pct") or 0)
        usage_session_reset = str(d.get("session_reset") or "?")
        usage_week_pct = int(d.get("week_pct") or 0)
        usage_week_reset = str(d.get("week_reset") or "?")
        face_pct_label.text = f"{usage_session_pct}%"
        face_pct_label.x = 126 - len(face_pct_label.text) * 6

        if usage_session_pct >= 90 and not usage_alerted:
            usage_alerted = True
            sfx.play("alert")
        elif usage_session_pct < previous - 20:      # window reset
            usage_alerted = False
            sfx.play("reset")
    else:
        face_pct_label.text = ""


def spotify_command(action):
    """Fire a control command at the bridge. Returns True on success."""
    if not online():
        return False
    d = bridge_get(f"{BRIDGE_BASE}/spotify/{action}")
    if d is None:
        sp_state_label.text = "no bridge"
        return False
    if not d.get("ok"):
        sp_state_label.text = fit(str(d.get("error") or "failed"))
    return bool(d.get("ok"))


def render_spotify():
    if not status_ok:
        sp_track_label.text = "Bridge offline"
        sp_artist_label.text = ""
        sp_state_label.text = ""
        draw_bar(sp_bar, 0)
        return
    if not sp_ok:
        sp_track_label.text = "Not connected"
        sp_artist_label.text = "run spotify.py"
        sp_state_label.text = ""
        draw_bar(sp_bar, 0)
        return
    if not sp_active:
        sp_track_label.text = "Nothing playing"
        sp_artist_label.text = ""
        sp_state_label.text = "open Spotify first"
        draw_bar(sp_bar, 0)
        return
    sp_track_label.text = fit(sp_track)
    sp_artist_label.text = fit(sp_artist)
    sp_state_label.text = "> PLAYING" if sp_playing else "|| PAUSED"
    draw_bar(sp_bar, sp_progress)


def human_minutes(total):
    """420 -> '7h00m'. The bridge sends ints; formatting is cheap here."""
    if total is None:
        return "?"
    if total <= 0:
        return "now"
    if total < 60:
        return f"{total}m"
    hours, minutes = divmod(total, 60)
    if hours < 24:
        return f"{hours}h{minutes:02d}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"


def wrap_two(text, width=21):
    """Split a title across two lines, breaking on a space where possible."""
    if len(text) <= width:
        return text, ""
    cut = text.rfind(" ", 0, width + 1)
    if cut <= 0:
        return text[:width], text[width:width * 2]
    return text[:cut], text[cut + 1:cut + 1 + width]


def render_calendar():
    if not status_ok:
        cal_index_label.text = ""
        cal_when_label.text = ""
        cal_line1_label.text = "Bridge offline"
        cal_line2_label.text = ""
        cal_in_label.text = ""
        return
    if not cal_ok:
        cal_index_label.text = ""
        cal_when_label.text = ""
        cal_line1_label.text = "Calendar not set up"
        cal_line2_label.text = "see README"
        cal_in_label.text = ""
        return
    if not events:
        cal_index_label.text = ""
        cal_when_label.text = ""
        cal_line1_label.text = "Nothing scheduled"
        cal_line2_label.text = ""
        cal_in_label.text = "next 7 days"
        return

    item = events[cal_index]
    cal_index_label.text = f"{cal_index + 1}/{len(events)}"
    when = str(item.get("when") or "")
    cal_when_label.text = when
    cal_when_label.x = max(40, 126 - len(when) * 6)
    line1, line2 = wrap_two(str(item.get("title") or ""))
    cal_line1_label.text = line1
    cal_line2_label.text = line2
    cal_in_label.text = "in " + human_minutes(item.get("in_min"))


def context_mood(idle_for, night):
    """What the face should show when the user hasn't picked something.

    Ordered by urgency: things you need to notice beat things that are
    merely pleasant. Returns None to leave the current mood alone.
    """
    if timer_active:
        return "angry"                       # focused, do not disturb
    if usage_ok and usage_session_pct >= USAGE_ALERT_PCT:
        return "surprised"                   # you're nearly out of window
    if night:
        return "sleepy"
    if sys_uptime_min and sys_uptime_min > UPTIME_TIRED_MIN:
        return "sleepy"                      # the PC could use a reboot
    if sp_playing:
        return "happy"
    if weather_mood != "neutral":
        return weather_mood
    return "neutral"


def render_usage():
    if usage_ok:
        usage_pct_label.text = f"{usage_session_pct}%"
        usage_scope_label.text = "SESSION"
        usage_reset_label.text = usage_session_reset
        usage_week_label.text = f"Week {usage_week_pct}%  in {usage_week_reset}"
        draw_bar(usage_bar, usage_session_pct)
    else:
        usage_pct_label.text = "--%"
        usage_scope_label.text = "OFFLINE" if not online() else "BRIDGE"
        usage_reset_label.text = "no wifi" if not online() else "offline"
        usage_week_label.text = "Is bridge.py running?"
        draw_bar(usage_bar, 0)


def render_system():
    if not status_ok:
        # Diagnose on the device itself: which address we have, and what the
        # last request actually said. Saves plugging into tio to find out.
        try:
            me = str(wifi.radio.ipv4_address or "no IP")
        except Exception:
            me = "no IP"
        cpu_label.text = "BRIDGE OFFLINE"
        temp_label.text = ""
        ram_label.text = fit("me " + me)
        ram_detail_label.text = ""
        if not online():
            sys_foot_label.text = "No wifi"
        else:
            sys_foot_label.text = fit(last_net_error or "no reply")
        draw_bar(cpu_bar, 0)
        draw_bar(ram_bar, 0)
        return
    cpu_label.text = f"CPU {sys_cpu}%"
    temp_label.text = f"{sys_temp}C" if sys_temp is not None else ""
    ram_label.text = f"RAM {sys_ram}%"
    ram_detail_label.text = f"{sys_ram_used:.1f}/{sys_ram_total:.0f}G"
    sys_foot_label.text = f"disk {sys_disk}%  up {sys_uptime}"
    draw_bar(cpu_bar, sys_cpu)
    draw_bar(ram_bar, sys_ram)


# --- Meeting popup ---
popup_showing = False
dismissed_event = None          # (title, start time) already waved away


def event_key():
    return (event_title, event_at)


def update_popup(now):
    """Show a full-screen warning inside the last few minutes before a meeting."""
    global popup_showing

    should_show = (
        cal_ok
        and event_title
        and event_in is not None
        and 0 <= event_in <= MEETING_WARN_MIN
        and dismissed_event != event_key()
    )

    if should_show and not popup_showing:
        popup_showing = True
        centre(popup_title, fit(event_title, 18))
        centre(popup_hint, "press 2 to dismiss")
        popup_group.hidden = False
        sfx.play("alert")
        eyes.startle(now=now)
    elif not should_show and popup_showing:
        popup_showing = False
        popup_group.hidden = True

    if popup_showing:
        if event_in <= 0:
            centre(popup_when, "NOW", char_w=12)
        else:
            centre(popup_when, f"in {event_in}m", char_w=12)


def dismiss_popup():
    global popup_showing, dismissed_event
    dismissed_event = event_key()
    popup_showing = False
    popup_group.hidden = True
    sfx.play("back")


# --- 5. BOOT ---
current_tab = 0
mode = "FACE"

boot_mark("network ready")

# The bridge hands us the wall clock over plain HTTP, so try that first.
# If the network stack is dead, fetch_status notices and resets on its own.
for boot_try in range(3):
    fetch_status(time.monotonic())
    if status_ok:
        break
    set_lines("Bridge", f"Waiting {boot_try + 1}/3")
    display.refresh()
    time.sleep(1.0)

# The HTTPS fallback only helps if the bridge is genuinely down. It will
# often fail on a cold boot anyway: the clock reads January 2000 until it's
# set, and TLS rejects certificates that look like they're from the future.
if not time_synced:
    get_time_https()
boot_mark("clock set" if time_synced else "clock NOT set -- will retry")

show_screen("face")
draw_dots(0)
set_brightness(1.0)
eyes.set_mood("happy")
eyes.intro(0.9)
sfx.play("boot")

boot_until = time.monotonic() + 1.1
while time.monotonic() < boot_until:
    n = time.monotonic()
    sfx.tick(n)
    eyes.tick(n)
    display.refresh()

boot_mark("ready")

# --- 6. THE MAIN LOOP ---
FACE_MOODS = ("neutral", "happy", "love", "sad", "angry", "surprised", "sleepy")
face_mood_index = 0
mood_locked_until = 0.0

TIMER_STEPS = (5, 10, 15, 20, 25, 30, 45, 60)
timer_step_index = 0
timer_active = False
timer_seconds = 0

IDLE_RETURN = 45.0
LONG_PRESS = 0.6
REPEAT_EVERY = 0.35
USAGE_REFRESH = 60.0
SYSTEM_REFRESH = 5.0
SPOTIFY_REFRESH = 4.0
BACKGROUND_REFRESH = 60.0        # keeps the meeting countdown honest
WIFI_CHECK = 8.0
RECONNECT_EVERY = 30.0

last_tick = time.monotonic()
last_input = time.monotonic()
last_wifi_check = 0.0
last_reconnect = 0.0

# Start as "was online" so a failed boot still counts as a drop and
# offers the game once, same as losing WiFi later would.
was_online = True
auto_games_at = 0.0

prev_mode_btn = True
prev_action_btn = True
mode_down_at = 0.0
mode_long_fired = False
action_down_at = 0.0
action_long_fired = False
action_repeat_at = None
action_hold_kind = None          # "timer" or "spotify"
lockout_until = 0.0


def enter_games_menu():
    global games_state
    games_state = "menu"
    render_games_menu()
    show_screen("games")


def launch_game(sfx_obj=None):
    """Start whichever entry the menu cursor is on, building it on demand."""
    global games_state
    games_hint.text = "loading..."
    display.refresh()
    if GAMES[game_index] == "Dino Run":
        ensure_dino()
        games_state = "dino"
        game.reset(to_title=True)
        show_screen("dino")
    else:
        ensure_ball()
        games_state = "eightball"
        ball.reset()
        show_screen("eightball")
    games_hint.text = "tap pick  hold start"
    if sfx_obj:
        sfx_obj.play("start")


def enter_mode(new_mode, now):
    """Switch screens and fetch anything the new screen needs."""
    global mode, mood_locked_until
    mode = new_mode
    draw_dots(MODES.index(mode))

    if mode == "FACE":
        show_screen("face")
        eyes.center(now=now)
        return

    if mode == "GAMES":
        enter_games_menu()
        return

    if mode == "CALENDAR":
        show_screen("calendar")
        cal_line1_label.text = "loading..."
        cal_line2_label.text = ""
        display.refresh()
        fetch_status(now)
        render_calendar()
        return

    if mode == "SPOTIFY":
        show_screen("spotify")
        fetch_status(now)
        render_spotify()
        return

    if mode == "WEATHER":
        show_screen("weather")
        if now - last_weather_fetch > WEATHER_REFRESH:
            wx_desc_label.text = "fetching..."
            display.refresh()
            fetch_weather(now)
        render_weather()
        return

    if mode == "USAGE":
        show_screen("usage")
        usage_pct_label.text = "..."
        usage_reset_label.text = "loading"
        usage_week_label.text = ""
        draw_bar(usage_bar, 0)
        display.refresh()
        fetch_status(now)
        render_usage()
        if usage_ok and usage_session_pct >= 90:
            eyes.set_mood("surprised")
            mood_locked_until = now + 60.0
        return

    if mode == "SYSTEM":
        show_screen("system")
        sys_foot_label.text = "reading..."
        display.refresh()
        fetch_status(now)
        render_system()
        return

    show_screen("text")


def go_home(now):
    global current_tab
    current_tab = 0
    enter_mode("FACE", now)


while True:
    now = time.monotonic()
    sfx.tick(now)

    mode_btn = btn_mode.value
    action_btn = btn_action.value

    # --- BUTTON 1: short press = next tab, hold = home ---
    if prev_mode_btn and not mode_btn and now >= lockout_until:
        mode_down_at = now
        mode_long_fired = False
        last_input = now

    if not mode_btn and not mode_long_fired and mode_down_at:
        if now - mode_down_at >= LONG_PRESS:
            mode_long_fired = True
            lockout_until = now + 0.2
            last_input = now
            sfx.play("home")
            eyes.center(now=now)
            go_home(now)

    if not prev_mode_btn and mode_btn:              # released
        if not mode_long_fired and mode_down_at and now >= lockout_until:
            lockout_until = now + 0.2
            last_input = now
            # inside a game, button 1 backs out to the menu first
            if mode == "GAMES" and games_state != "menu":
                sfx.play("back")
                enter_games_menu()
            else:
                sfx.play("tab")
                eyes.look(-1.0, 0.0, now=now)
                current_tab = (current_tab + 1) % len(MODES)
                enter_mode(MODES[current_tab], now)
        mode_down_at = 0.0
        mode_long_fired = False

    # --- BUTTON 2: context-dependent, with a hold gesture on some tabs ---
    if prev_action_btn and not action_btn and now >= lockout_until:
        action_down_at = now
        action_long_fired = False
        action_repeat_at = None
        action_hold_kind = None
        last_input = now

        if popup_showing:
            pass                                    # handled on release
        elif mode == "GAMES" and games_state == "dino":
            game.press(sfx)                         # games need instant response
        elif mode == "GAMES" and games_state == "eightball":
            ball.press(sfx)
        elif mode == "GAMES":                       # the menu
            action_hold_kind = "games"
            action_repeat_at = now + LONG_PRESS
        elif mode == "TIMER" and not timer_active:
            action_hold_kind = "timer"
            action_repeat_at = now + LONG_PRESS
        elif mode == "SPOTIFY":
            action_hold_kind = "spotify"
            action_repeat_at = now + LONG_PRESS

    if not action_btn and action_down_at and action_repeat_at:
        if now >= action_repeat_at:
            action_long_fired = True
            last_input = now
            if action_hold_kind == "timer":
                action_repeat_at = now + REPEAT_EVERY     # keep stepping
                timer_step_index = (timer_step_index + 1) % len(TIMER_STEPS)
                sfx.tone(1100 + timer_step_index * 90, 0.04)
            elif action_hold_kind == "games":
                action_repeat_at = None                   # fires once
                launch_game(sfx)
            else:                                          # spotify: skip once
                action_repeat_at = None
                sfx.play("select")
                sp_state_label.text = "skipping..."
                display.refresh()
                spotify_command("next")
                fetch_status(now)
                render_spotify()

    if not prev_action_btn and action_btn:          # released
        if popup_showing:
            dismiss_popup()
            lockout_until = now + 0.2
            last_input = now
        elif (mode == "GAMES" and games_state != "menu"):
            pass                            # already handled on press
        elif (not action_long_fired
                and action_down_at and now >= lockout_until):
            lockout_until = now + 0.2
            last_input = now
            eyes.look(1.0, 0.0, now=now)

            if mode == "GAMES":             # menu: step the cursor
                game_index = (game_index + 1) % len(GAMES)
                render_games_menu()
                sfx.tone(1200 + game_index * 120, 0.04)

            elif mode == "FACE":
                face_mood_index = (face_mood_index + 1) % len(FACE_MOODS)
                eyes.set_mood(FACE_MOODS[face_mood_index])
                eyes.blink(now=now)
                mood_locked_until = now + 20.0
                sfx.tone(900 + face_mood_index * 150, 0.05)

            elif mode == "CALENDAR":
                sfx.play("select")
                if events:
                    cal_index = (cal_index + 1) % len(events)
                render_calendar()

            elif mode == "SPOTIFY":
                sfx.play("select")
                spotify_command("playpause")
                fetch_status(now)
                render_spotify()

            else:
                sfx.play("select")

                if mode == "TIMER":
                    if not timer_active:
                        timer_active = True
                        timer_seconds = TIMER_STEPS[timer_step_index] * 60
                        last_tick = now
                        eyes.set_mood("angry")
                    else:
                        timer_active = False
                        timer_seconds = 0
                        eyes.set_mood("neutral")

                elif mode == "WEATHER":
                    wx_desc_label.text = "fetching..."
                    display.refresh()
                    fetch_weather(now)
                    render_weather()

                elif mode == "USAGE":
                    usage_reset_label.text = "refresh"
                    display.refresh()
                    fetch_status(now)
                    render_usage()

                elif mode == "SYSTEM":
                    fetch_status(now)
                    render_system()

        action_down_at = 0.0
        action_long_fired = False
        action_repeat_at = None
        action_hold_kind = None

    prev_mode_btn = mode_btn
    prev_action_btn = action_btn

    # --- TIMER COUNTDOWN LOGIC ---
    if timer_active:
        if now - last_tick >= 1.0:
            timer_seconds -= 1
            last_tick = now
        if timer_seconds <= 0:
            timer_active = False
            current_tab = MODES.index("TIMER")
            enter_mode("TIMER", now)
            set_lines("00:00", "TIME IS UP!")
            eyes.set_mood("happy")
            mood_locked_until = now + 20.0
            sfx.play("alarm")

    # --- WI-FI WATCHDOG ---
    # Acts on *transitions*, not on state. The old version forced the games
    # tab every time it found us offline, so you could never leave it.
    if now - last_wifi_check > WIFI_CHECK:
        last_wifi_check = now
        is_online = online()

        if not is_online:
            if was_online:
                # just dropped: offer the game, exactly once
                print("Wi-Fi lost")
                if mode != "GAMES":
                    current_tab = MODES.index("GAMES")
                    enter_mode("GAMES", now)
                    game_index = 0              # Dino Run
                    launch_game()
                    auto_games_at = now

            # connect() blocks for seconds, so never mid-run
            mid_run = (games_state == "dino" and game is not None
                       and game.state == DINO_PLAYING)
            if now - last_reconnect > RECONNECT_EVERY and not mid_run:
                last_reconnect = now
                if connect_wifi(attempts=1, show=False):
                    is_online = True

        if is_online and not was_online:
            # just came back
            print("Wi-Fi restored")
            rebuild_session()
            fetch_status(now)
            # if we dragged you into the game and you never touched it,
            # put you back where you'd expect to be
            if auto_games_at and last_input <= auto_games_at:
                go_home(now)
            auto_games_at = 0.0

        was_online = is_online

    # --- BACKGROUND POLL ---
    # Once a minute when healthy; every 10s while the bridge is down, so a
    # cold boot that missed it recovers quickly rather than a minute later.
    poll_every = BACKGROUND_REFRESH if status_ok else 10.0
    if (mode not in ("USAGE", "SYSTEM", "SPOTIFY", "CALENDAR", "GAMES")
            and now - last_status_fetch > poll_every):
        fetch_status(now)

    # --- MEETING POPUP ---
    if mode != "GAMES" or games_state == "menu":
        update_popup(now)
    elif popup_showing:
        popup_showing = False
        popup_group.hidden = True

    # --- IDLE BEHAVIOUR ---
    # Don't yank the user off a tab they're actively using: while music is
    # playing, the Spotify tab is the controls, so leave it alone.
    idle_for = now - last_input
    holding_tab = mode == "SPOTIFY" and sp_playing
    if (mode not in ("FACE", "GAMES") and not timer_active
            and not holding_tab and idle_for > IDLE_RETURN):
        go_home(now)

    # --- BURN-IN PROTECTION ---
    if now >= next_shift:
        next_shift = now + SHIFT_INTERVAL
        shift_index = (shift_index + 1) % len(SHIFT_OFFSETS)
        main_group.x, main_group.y = SHIFT_OFFSETS[shift_index]

    t = time.localtime()
    night = t.tm_hour >= 23 or t.tm_hour < 7
    if timer_active or mode == "GAMES" or popup_showing:
        set_brightness(1.0)
    elif night:
        set_brightness(0.15)
    else:
        set_brightness(1.0)

    # --- UPDATE THE SCREEN ---
    if mode == "FACE":
        face_time_label.text = f"{t.tm_hour:02d}:{t.tm_min:02d}"
        face_date_label.text = (f"{weekday_name(t.tm_year, t.tm_mon, t.tm_mday)}"
                                f" {t.tm_mday:02d} {MONTHS[t.tm_mon - 1]}")
        face_date_label.x = (128 - len(face_date_label.text) * 6) // 2
        # A manual pick (button 2) holds for 20s; otherwise context decides.
        if now >= mood_locked_until:
            wanted = context_mood(idle_for, night)
            if wanted and wanted != eyes.mood:
                eyes.set_mood(wanted)
        eyes.tick(now)

    elif mode == "GAMES":
        if games_state == "dino":
            game.tick(now, sfx)
        elif games_state == "eightball":
            ball.tick(now, sfx)

    elif mode == "CALENDAR":
        if now - last_status_fetch > USAGE_REFRESH:
            fetch_status(now)
            render_calendar()

    elif mode == "SPOTIFY":
        if now - last_status_fetch > SPOTIFY_REFRESH:
            fetch_status(now)
            render_spotify()

    elif mode == "WEATHER":
        wx_time_label.text = f"{t.tm_hour:02d}:{t.tm_min:02d}"
        if now - last_weather_fetch > WEATHER_REFRESH:
            fetch_weather(now)
            render_weather()

    elif mode == "USAGE":
        if now - last_status_fetch > USAGE_REFRESH:
            fetch_status(now)
            render_usage()

    elif mode == "SYSTEM":
        if now - last_status_fetch > SYSTEM_REFRESH:
            fetch_status(now)
            render_system()

    elif mode == "TIMER":
        if timer_active:
            set_lines(f"{timer_seconds // 60:02d}:{timer_seconds % 60:02d}",
                      "Timer Running")
        else:
            set_lines(f"{TIMER_STEPS[timer_step_index]:02d}:00",
                      "hold 2 to change")

    display.refresh()
