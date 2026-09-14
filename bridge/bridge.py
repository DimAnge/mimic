#!/usr/bin/env python3
"""
Desky bridge -- serves Claude usage, system stats and your next meeting.

Runs `ccusage json`, reads /proc, and fetches your Google Calendar via its
secret iCal URL. Everything is re-served in a shape a microcontroller can
handle: plain integers and pre-formatted strings, so the Pico never has to
parse an ISO timestamp (CircuitPython has no datetime).

Run it:      python3 bridge.py            (or ~/desky-venv/bin/python bridge.py)
Check it:    curl http://localhost:8080/status

Calendar support needs two libraries. Without them everything else still
works and cal_ok comes back false:

    python3 -m venv ~/desky-venv
    ~/desky-venv/bin/pip install icalendar recurring-ical-events

The iCal URL is a bearer credential -- anyone holding it can read your
calendar. Keep it in ~/.desky-ical-url with chmod 600. It never leaves
this machine; the Pico only receives a title and a countdown.
"""

import json
import os
import shutil
import subprocess
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
USAGE_CACHE_SECONDS = 60      # ccusage is slow-ish, don't hammer it
SYSTEM_CACHE_SECONDS = 4      # /proc is cheap
CALENDAR_CACHE_SECONDS = 300  # Google rate-limits the iCal endpoint
LOOK_AHEAD_HOURS = 14

# Override with CCUSAGE_BIN=/full/path/to/ccusage if it isn't on PATH
CCUSAGE = os.environ.get("CCUSAGE_BIN") or shutil.which("ccusage")

ICAL_FILE = os.path.expanduser("~/.desky-ical-url")

try:
    import icalendar
    import recurring_ical_events
    CALENDAR_LIBS = True
except ImportError:
    CALENDAR_LIBS = False

try:
    import spotify
    SPOTIFY_MODULE = True
except ImportError:
    SPOTIFY_MODULE = False

SPOTIFY_CACHE_SECONDS = 3     # the track changes often; keep this snappy

_usage_cache = {"data": None, "at": 0.0}
_system_cache = {"data": None, "at": 0.0}
_calendar_cache = {"cal": None, "at": 0.0, "ok": False}
_spotify_cache = {"data": None, "at": 0.0}


def ical_url():
    url = os.environ.get("DESKY_ICAL_URL")
    if url:
        return url.strip()
    try:
        with open(ICAL_FILE) as f:
            return f.read().strip()
    except Exception:
        return None


# --------------------------------------------------------------- helpers
def human_delta(iso_string):
    """'2026-09-04T17:20:00+00:00' -> '3h25m' (or '45m', or '2d0h')."""
    if not iso_string:
        return "?"
    try:
        target = datetime.fromisoformat(iso_string)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
        seconds = (target - datetime.now(timezone.utc)).total_seconds()
    except Exception:
        return "?"

    if seconds <= 0:
        return "now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"


def human_uptime(seconds):
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m"
    hours, minutes = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h{minutes}m"
    days, hours = divmod(hours, 24)
    return f"{days}d{hours}h"


# ----------------------------------------------------------- system stats
def _cpu_counters():
    with open("/proc/stat") as f:
        fields = [int(v) for v in f.readline().split()[1:]]
    idle = fields[3] + (fields[4] if len(fields) > 4 else 0)
    return sum(fields), idle


def cpu_percent(sample=0.2):
    """Two /proc/stat reads a fraction of a second apart."""
    try:
        total1, idle1 = _cpu_counters()
        time.sleep(sample)
        total2, idle2 = _cpu_counters()
        d_total = total2 - total1
        if d_total <= 0:
            return 0
        d_idle = idle2 - idle1
        return max(0, min(100, int(round(100.0 * (d_total - d_idle) / d_total))))
    except Exception:
        return 0


def mem_info():
    """Returns (percent_used, used_GiB, total_GiB)."""
    try:
        values = {}
        with open("/proc/meminfo") as f:
            for line in f:
                key, _, rest = line.partition(":")
                values[key] = int(rest.split()[0])       # kB
        total = values.get("MemTotal", 0)
        available = values.get("MemAvailable", values.get("MemFree", 0))
        if total <= 0:
            return 0, 0.0, 0.0
        used = total - available
        return (int(round(100.0 * used / total)),
                round(used / 1048576.0, 1),
                round(total / 1048576.0, 1))
    except Exception:
        return 0, 0.0, 0.0


def cpu_temp():
    """Hottest plausible thermal zone, in Celsius."""
    base = "/sys/class/thermal"
    hottest = None
    try:
        for name in os.listdir(base):
            if not name.startswith("thermal_zone"):
                continue
            try:
                with open(os.path.join(base, name, "temp")) as f:
                    celsius = int(f.read().strip()) / 1000.0
            except Exception:
                continue
            if 0 < celsius < 150 and (hottest is None or celsius > hottest):
                hottest = celsius
    except Exception:
        pass
    return int(round(hottest)) if hottest is not None else None


def read_system():
    ram_pct, ram_used, ram_total = mem_info()
    uptime_min = 0
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        uptime = human_uptime(seconds)
        uptime_min = int(seconds // 60)
    except Exception:
        uptime = "?"
    try:
        usage = shutil.disk_usage("/")
        disk_pct = int(round(100.0 * usage.used / usage.total))
    except Exception:
        disk_pct = 0

    return {
        "cpu_pct": cpu_percent(),
        "ram_pct": ram_pct,
        "ram_used_gb": ram_used,
        "ram_total_gb": ram_total,
        "temp_c": cpu_temp(),
        "disk_pct": disk_pct,
        "uptime": uptime,
        "uptime_min": uptime_min,
    }


# ---------------------------------------------------------------- calendar
def load_calendar():
    """Fetch and parse the iCal feed, cached."""
    now = time.time()
    if (_calendar_cache["cal"] is not None
            and now - _calendar_cache["at"] < CALENDAR_CACHE_SECONDS):
        return _calendar_cache["cal"]

    _calendar_cache["at"] = now
    url = ical_url()
    if not url or not CALENDAR_LIBS:
        _calendar_cache["cal"] = None
        _calendar_cache["ok"] = False
        return None

    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            raw = response.read()
        _calendar_cache["cal"] = icalendar.Calendar.from_ical(raw)
        _calendar_cache["ok"] = True
    except Exception as exc:
        print("Calendar fetch failed:", exc)
        _calendar_cache["cal"] = None
        _calendar_cache["ok"] = False
    return _calendar_cache["cal"]


def upcoming_events(limit=3):
    """The next few timed events that haven't finished, soonest first."""
    calendar = load_calendar()
    if calendar is None:
        return None

    local_now = datetime.now().astimezone()
    window_start = local_now - timedelta(hours=1)
    window_end = local_now + timedelta(hours=LOOK_AHEAD_HOURS)

    try:
        occurrences = recurring_ical_events.of(calendar).between(
            window_start, window_end)
    except Exception as exc:
        print("Calendar expand failed:", exc)
        return None

    found = []
    for event in occurrences:
        start = event["DTSTART"].dt
        # all-day entries come back as date objects -- birthdays, not meetings
        if not isinstance(start, datetime):
            continue
        if start.tzinfo is None:
            start = start.replace(tzinfo=local_now.tzinfo)

        end = event.get("DTEND")
        end = end.dt if end is not None else start + timedelta(minutes=30)
        if isinstance(end, datetime) and end.tzinfo is None:
            end = end.replace(tzinfo=local_now.tzinfo)
        if isinstance(end, datetime) and end <= local_now:
            continue                      # already finished

        found.append((start, str(event.get("SUMMARY", "(no title)"))))

    found.sort(key=lambda pair: pair[0])

    out = []
    for start, title in found[:limit]:
        local_start = start.astimezone(local_now.tzinfo)
        out.append({
            "title": title[:40],
            "when": local_start.strftime("%a %H:%M"),
            "at": local_start.strftime("%H:%M"),
            "in_min": int((start - local_now).total_seconds() // 60),
        })
    return out


def calendar_payload():
    """Popup fields for the soonest event, plus a short list for the tab."""
    blank = {"cal_ok": False, "event_title": "", "event_in": None,
             "event_at": "", "event_running": False, "events": []}

    events = upcoming_events()
    if events is None:
        return blank
    if not events:
        return {"cal_ok": True, "event_title": "", "event_in": None,
                "event_at": "", "event_running": False, "events": []}

    first = events[0]
    return {
        "cal_ok": True,
        "event_title": first["title"],
        "event_in": first["in_min"],             # negative once it has begun
        "event_at": first["at"],
        "event_running": first["in_min"] <= 0,
        "events": events,
    }


# ------------------------------------------------------------ claude usage
def read_usage():
    if CCUSAGE is None:
        return {"usage_ok": False}
    try:
        raw = subprocess.run([CCUSAGE, "json"],
                             capture_output=True, text=True, timeout=30)
        if raw.returncode != 0:
            return {"usage_ok": False}
        d = json.loads(raw.stdout)
    except Exception as exc:
        print("ccusage error:", exc)
        return {"usage_ok": False}

    session = d.get("session") or {}
    week = d.get("7d") or {}
    return {
        "usage_ok": True,
        "plan": d.get("plan", "?"),
        "session_pct": int(session.get("pct") or 0),
        "session_resets_at": session.get("resets_at"),
        "week_pct": int(week.get("pct") or 0),
        "week_resets_at": week.get("resets_at"),
    }


def build_payload():
    now = time.time()

    if _usage_cache["data"] is None or now - _usage_cache["at"] > USAGE_CACHE_SECONDS:
        _usage_cache["data"] = read_usage()
        _usage_cache["at"] = now

    if _system_cache["data"] is None or now - _system_cache["at"] > SYSTEM_CACHE_SECONDS:
        _system_cache["data"] = read_system()
        _system_cache["at"] = now

    usage = dict(_usage_cache["data"])
    # Countdowns are recomputed per request so the Pico never sees a stale one
    usage["session_reset"] = human_delta(usage.pop("session_resets_at", None))
    usage["week_reset"] = human_delta(usage.pop("week_resets_at", None))

    if SPOTIFY_MODULE:
        if (_spotify_cache["data"] is None
                or now - _spotify_cache["at"] > SPOTIFY_CACHE_SECONDS):
            _spotify_cache["data"] = spotify.now_playing()
            _spotify_cache["at"] = now
        spotify_state = _spotify_cache["data"]
    else:
        spotify_state = {"sp_ok": False, "sp_active": False,
                         "sp_playing": False, "sp_track": "",
                         "sp_artist": "", "sp_progress": 0}

    payload = {"ok": True}
    payload.update(usage)
    payload.update(_system_cache["data"])
    payload.update(calendar_payload())   # cheap: the parsed calendar is cached
    payload.update(spotify_state)

    # The Pico's own time sync is an HTTPS call, and a TLS handshake on a
    # microcontroller costs seconds at boot. We're already talking to it over
    # plain HTTP, so hand over the wall clock and let it skip that entirely.
    local = datetime.now()
    payload["clock"] = [local.year, local.month, local.day,
                        local.hour, local.minute, local.second]
    return payload


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj):
        """Write a JSON response, tolerating a client that hung up."""
        body = json.dumps(obj).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Someone pressed Ctrl-C on curl, or the Pico timed out. Normal.
            pass

    def do_GET(self):
        route = self.path.rstrip("/")

        # Control routes are GETs so the Pico can fire them with one line.
        if route.startswith("/spotify/"):
            action = route.rsplit("/", 1)[-1]
            if not SPOTIFY_MODULE:
                result = {"ok": False, "error": "spotify.py not found"}
            else:
                ok, message = spotify.control(action)
                result = {"ok": ok, "error": None if ok else message}
                _spotify_cache["at"] = 0.0        # force a re-read next poll
            self._send_json(result)
            return

        if route not in ("", "/status"):
            self.send_error(404)
            return
        self._send_json(build_payload())

    def log_message(self, *args):
        pass          # keep the terminal quiet


if __name__ == "__main__":
    if CCUSAGE is None:
        print("WARNING: ccusage not found on PATH. "
              "Set CCUSAGE_BIN to its full path. System stats still work.")
    if not CALENDAR_LIBS:
        print("WARNING: icalendar / recurring-ical-events not installed. "
              "Calendar disabled; everything else still works.")
    elif not ical_url():
        print(f"WARNING: no iCal URL. Put your Google secret iCal address in "
              f"{ICAL_FILE}")
    if not SPOTIFY_MODULE:
        print("WARNING: spotify.py not next to bridge.py. Spotify disabled.")
    elif not spotify.load_tokens().get("refresh_token"):
        print("WARNING: Spotify not authorized yet. Run:  python spotify.py")
    print(f"Desky bridge listening on port {PORT}")
    print(f"Test locally:  curl http://localhost:{PORT}/status")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
