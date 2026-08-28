"""Linux notes for the Python host (serial + pynput)."""

from __future__ import annotations

import os
import sys

SERIAL_HELP = """
Linux serial access
  1. Plug in the CYD. You should see /dev/ttyUSB0 or /dev/ttyACM0
     (dmesg | tail). CH340/CP2102 usually need no extra driver.
  2. Your user must be in group dialout (or uucp on some distros):
       sudo usermod -aG dialout $USER
     then log out and back in. Check: groups | grep dialout
  3. If the port exists but open fails: ls -l /dev/ttyUSB0
     and make sure you are not using a charge-only cable.

Linux key listening (real typing, not the testbench)
  pynput needs a graphical session (X11 or Wayland).
  Headless SSH will not see keys — use tools/cyd_testbench.py instead.
  If keys still fail in a desktop session:
       sudo usermod -aG input $USER
"""


def on_linux() -> bool:
    return sys.platform.startswith("linux")


def looks_like_permission_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(s in text for s in ("permission denied", "errno 13", "access denied"))


def device_writable(path: str) -> bool:
    try:
        return os.access(path, os.R_OK | os.W_OK)
    except OSError:
        return False
