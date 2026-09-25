# code.py -- keeps Desky alive.
#
# The real program lives in app.py. This file does two jobs around it.
#
# 1. STUCK-NETWORK RECOVERY.
#    On a cold power-on the Pico can join WiFi and get an address, yet pass
#    no traffic at all: every connection times out (EINPROGRESS) and even DNS
#    fails. Once in that state it never recovers by itself. A soft reset
#    clears it -- but only once the network is genuinely ready, which can
#    take a minute or two after power-on.
#    app.py detects the dead stack (bridge AND DNS both failing) and raises
#    NetworkStuck. We answer with a soft reset. A counter in non-volatile
#    memory caps how many times, so a truly broken network can't loop forever.
#
# 2. CRASH RECOVERY.
#    When code.py raises, CircuitPython prints the error and then waits for
#    a keypress on the serial console. On a desk with no computer attached
#    that looks like the device is dead. Instead: log it, wait, restart.
#
# Ctrl-C in tio still drops you into the REPL: KeyboardInterrupt is not an
# Exception subclass, so it passes straight through the handler below.

import time
import supervisor
import microcontroller

RESTART_DELAY = 5     # seconds -- long enough to read an error in tio

# A genuine power-on gets a fresh budget of stuck-network restarts.
# Resets we trigger ourselves don't count as power-ons, so the budget
# carries across them.
if supervisor.runtime.run_reason == supervisor.RunReason.STARTUP:
    try:
        if microcontroller.nvm[0] != 0:
            microcontroller.nvm[0] = 0
    except Exception:
        pass


try:
    import app        # runs the whole program; only returns if it crashes
except Exception as exc:
    if type(exc).__name__ == "NetworkStuck":
        # Expected, not a crash: app.py asked for a clean restart.
        print("Soft-resetting to clear the network stack...")
        supervisor.reload()

    print()
    print("=" * 40)
    print("Desky crashed:")
    try:
        import traceback
        traceback.print_exception(exc)
    except Exception:
        print(repr(exc))
    print(f"Restarting in {RESTART_DELAY}s...")
    print("=" * 40)
    time.sleep(RESTART_DELAY)
    supervisor.reload()
