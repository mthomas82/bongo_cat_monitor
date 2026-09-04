#!/usr/bin/env python3
"""Load pystray without crashing when a forced Linux backend is missing."""

import importlib
import os
import sys


def load_pystray(environ=None, importer=None, loaded_modules=None):
    env = os.environ if environ is None else environ
    importer = importer or importlib.import_module
    loaded_modules = sys.modules if loaded_modules is None else loaded_modules

    def try_import():
        for key in list(loaded_modules):
            if key == "pystray" or key.startswith("pystray."):
                del loaded_modules[key]
        return importer("pystray")

    requested = env.get("PYSTRAY_BACKEND")
    if requested:
        try:
            return try_import()
        except Exception:
            env.pop("PYSTRAY_BACKEND", None)

    try:
        return try_import()
    except Exception:
        return None
