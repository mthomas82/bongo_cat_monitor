#!/usr/bin/env python3
"""Load pystray without crashing when a forced Linux backend is missing."""

import importlib
import os
import sys

LINUX_BACKENDS = ("appindicator", "gtk", "xorg")

TRAY_HELP = """
Ubuntu tray icon (optional; typing works without it)

  sudo apt install gir1.2-ayatanaappindicator3-0.1 python3-gi python3-gi-cairo gnome-shell-extension-appindicator

Let this project's Python see those Ubuntu libraries. In .venv/pyvenv.cfg
set:

  include-system-site-packages = true

Then start the host again. Ubuntu may hide the cat behind a small arrow
on the top bar.
"""


def load_pystray(environ=None, importer=None, loaded_modules=None):
    env = os.environ if environ is None else environ
    importer = importer or importlib.import_module
    loaded_modules = sys.modules if loaded_modules is None else loaded_modules

    def try_import():
        for key in list(loaded_modules):
            if key == "pystray" or key.startswith("pystray."):
                del loaded_modules[key]
        return importer("pystray")

    names = []
    requested = env.get("PYSTRAY_BACKEND")
    if requested:
        names.append(requested)
    if sys.platform.startswith("linux"):
        for name in LINUX_BACKENDS:
            if name not in names:
                names.append(name)

    for name in names:
        env["PYSTRAY_BACKEND"] = name
        try:
            return try_import()
        except Exception:
            continue

    env.pop("PYSTRAY_BACKEND", None)
    try:
        return try_import()
    except Exception:
        return None
