#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from tray_backend import load_pystray  # noqa: E402


class FakePystray:
    pass


class LoadPystrayTests(unittest.TestCase):
    def test_forced_appindicator_missing_falls_back_to_default(self):
        env = {"PYSTRAY_BACKEND": "appindicator"}
        calls = []

        def importer(name):
            calls.append(env.get("PYSTRAY_BACKEND"))
            if env.get("PYSTRAY_BACKEND") == "appindicator":
                raise ValueError("Namespace AyatanaAppIndicator3 not available")
            return FakePystray()

        mod = load_pystray(environ=env, importer=importer, loaded_modules={})
        self.assertIsInstance(mod, FakePystray)
        self.assertNotEqual(env.get("PYSTRAY_BACKEND"), "appindicator")
        self.assertGreaterEqual(len(calls), 2)

    def test_all_backends_missing_returns_none(self):
        env = {"PYSTRAY_BACKEND": "appindicator"}

        def importer(name):
            raise ValueError("Namespace AyatanaAppIndicator3 not available")

        mod = load_pystray(environ=env, importer=importer, loaded_modules={})
        self.assertIsNone(mod)

    def test_default_backend_ok_without_env(self):
        env = {}

        def importer(name):
            return FakePystray()

        mod = load_pystray(environ=env, importer=importer, loaded_modules={})
        self.assertIsInstance(mod, FakePystray)

    def test_linux_tries_gtk_after_appindicator_fails(self):
        env = {}
        calls = []

        def importer(name):
            calls.append(env.get("PYSTRAY_BACKEND"))
            if env.get("PYSTRAY_BACKEND") != "gtk":
                raise ValueError("Namespace AyatanaAppIndicator3 not available")
            return FakePystray()

        mod = load_pystray(environ=env, importer=importer, loaded_modules={})
        self.assertIsInstance(mod, FakePystray)
        self.assertIn("appindicator", calls)
        self.assertIn("gtk", calls)


if __name__ == "__main__":
    unittest.main()
