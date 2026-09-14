#!/usr/bin/env python3
"""
cal_debug.py -- show exactly what your iCal feed contains.

    ~/desky-venv/bin/python cal_debug.py

Prints the calendar's own name, how many raw events are in the file, and
every occurrence it can find from yesterday to a week out. If your meeting
isn't listed here, the bridge can't see it either -- and the reason will
usually be obvious from the calendar name.
"""

import os
import urllib.request
from datetime import datetime, timedelta

import icalendar
import recurring_ical_events

ICAL_FILE = os.path.expanduser("~/.desky-ical-url")


def main():
    url = os.environ.get("DESKY_ICAL_URL")
    if not url:
        with open(ICAL_FILE) as f:
            url = f.read().strip()

    print("Fetching feed...")
    with urllib.request.urlopen(url, timeout=30) as response:
        raw = response.read()
    print(f"Downloaded {len(raw)} bytes\n")

    calendar = icalendar.Calendar.from_ical(raw)

    name = calendar.get("X-WR-CALNAME", "(unnamed)")
    print(f"Calendar name : {name}")
    print("  ^^ is this the calendar your meeting is actually on?\n")

    raw_events = [c for c in calendar.walk("VEVENT")]
    print(f"Raw VEVENT blocks in file: {len(raw_events)}")

    now = datetime.now().astimezone()
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)
    occurrences = recurring_ical_events.of(calendar).between(start, end)
    occurrences.sort(key=lambda e: str(e["DTSTART"].dt))

    print(f"Occurrences between {start:%d %b %H:%M} and {end:%d %b %H:%M}: "
          f"{len(occurrences)}\n")

    if not occurrences:
        print("Nothing in that window. Either the feed is stale, or this")
        print("isn't the calendar the event lives on.")
        return

    for event in occurrences:
        begins = event["DTSTART"].dt
        title = str(event.get("SUMMARY", "(no title)"))
        if isinstance(begins, datetime):
            kind = "timed  "
            when = begins.strftime("%a %d %b %H:%M")
        else:
            kind = "all-day"      # skipped by the bridge on purpose
            when = begins.strftime("%a %d %b")
        print(f"  [{kind}] {when}  {title}")

    print("\nThe bridge ignores all-day entries -- birthdays and holidays")
    print("aren't meetings and shouldn't trigger a popup.")


if __name__ == "__main__":
    main()
