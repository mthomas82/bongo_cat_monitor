#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from tray_backend import load_pystray, start_tray_icon  # noqa: E402


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


class FakeIcon:
    def __init__(self):
        self.run_calls = 0
        self.detached_calls = 0

    def run(self):
        self.run_calls += 1

    def run_detached(self):
        self.detached_calls += 1


class StartTrayIconTests(unittest.TestCase):
    def test_linux_runs_icon_on_a_thread_not_detached(self):
        icon = FakeIcon()
        started = []

        class FakeThread:
            def __init__(self, target=None, daemon=None):
                self.target = target
                self.daemon = daemon

            def start(self):
                started.append(self)
                self.target()

        mode = start_tray_icon(icon, platform="linux", thread_cls=FakeThread)
        self.assertEqual(mode, "run-thread")
        self.assertEqual(icon.run_calls, 1)
        self.assertEqual(icon.detached_calls, 0)
        self.assertEqual(len(started), 1)
        self.assertTrue(started[0].daemon)

    def test_macos_uses_run_detached(self):
        icon = FakeIcon()
        mode = start_tray_icon(icon, platform="darwin")
        self.assertEqual(mode, "run_detached")
        self.assertEqual(icon.run_calls, 0)
        self.assertEqual(icon.detached_calls, 1)


if __name__ == "__main__":
    unittest.main()
