#!/usr/bin/env python3
"""Load pystray without crashing when a forced Linux backend is missing."""

import importlib
import os
import sys
import threading

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


def start_tray_icon(icon, platform=None, thread_cls=None):
    """Start pystray so the icon can actually appear.

    Linux AppIndicator/GTK only show an icon if a GLib loop runs.
    run_detached() does not start that loop. icon.run() does, so Linux
    runs it on a daemon thread while the keyboard listener keeps the
    main thread. macOS still needs run_detached().
    """
    platform = sys.platform if platform is None else platform
    thread_cls = threading.Thread if thread_cls is None else thread_cls
    if str(platform).startswith("linux"):
        thread_cls(target=icon.run, daemon=True).start()
        return "run-thread"
    icon.run_detached()
    return "run_detached"
