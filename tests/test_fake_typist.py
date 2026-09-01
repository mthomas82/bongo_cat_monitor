#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from fake_typist import ListSink, play_session  # noqa: E402


class PlaySessionTests(unittest.TestCase):
    def test_idle_session_ends_with_stop(self):
        sink = ListSink()
        play_session(sink, wpm=0, duration_s=0.0, now=lambda: 0.0, sleep=lambda _: None)
        self.assertIn("STOP", sink.commands)
        self.assertTrue(any(c.startswith("STATS:") and "WPM:0" in c for c in sink.commands))

    def test_typing_session_sends_speed_keepalive_then_stop(self):
        sink = ListSink()
        ticks = [0.0]

        def now():
            return ticks[0]

        def sleep(dt):
            ticks[0] += dt

        play_session(sink, wpm=40, duration_s=2.5, now=now, sleep=sleep)
        speeds = [c for c in sink.commands if c.startswith("SPEED:")]
        self.assertGreaterEqual(len(speeds), 2)  # initial + keepalive
        self.assertEqual(sink.commands[-1], "STOP")

    def test_demo_script_has_named_phases(self):
        from fake_typist import DEMO_PHASES

        names = [p[0] for p in DEMO_PHASES]
        self.assertEqual(names[0], "idle")
        self.assertIn("streak", names)
        self.assertIn("slow", names)


if __name__ == "__main__":
    unittest.main()
