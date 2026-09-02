#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from protocol import (  # noqa: E402
    idle_milestone_command,
    keystroke_interval_seconds,
    mode_command,
    reaction_command,
    streak_commands,
    tap_command,
    typing_commands,
    wpm_to_speed_ms,
)


class WpmToSpeedTests(unittest.TestCase):
    def test_zero_wpm_is_slowest(self):
        self.assertEqual(wpm_to_speed_ms(0), 500)

    def test_higher_wpm_is_faster_delay(self):
        self.assertLess(wpm_to_speed_ms(80), wpm_to_speed_ms(20))

    def test_caps_at_200_wpm(self):
        self.assertEqual(wpm_to_speed_ms(200), wpm_to_speed_ms(999))
        self.assertGreaterEqual(wpm_to_speed_ms(200), 30)


class TypingCommandTests(unittest.TestCase):
    def test_idle_sends_stop_and_stats(self):
        cmds = typing_commands(wpm=0, cpu=10, ram=20)
        self.assertIn("STOP", cmds)
        self.assertIn("STREAK_OFF", cmds)
        self.assertIn("STATS:CPU:10,RAM:20,WPM:0", cmds)
        self.assertFalse(any(c.startswith("SPEED:") for c in cmds))

    def test_fast_typing_sends_speed_and_streak(self):
        cmds = typing_commands(wpm=80, cpu=1, ram=2)
        self.assertTrue(any(c.startswith("SPEED:") for c in cmds))
        self.assertIn("STREAK_ON", cmds)
        self.assertIn("STATS:CPU:1,RAM:2,WPM:80", cmds)
        self.assertNotIn("STOP", cmds)

    def test_slow_typing_no_streak(self):
        cmds = typing_commands(wpm=15)
        self.assertIn("STREAK_OFF", cmds)
        self.assertNotIn("STREAK_ON", cmds)


class StreakHelperTests(unittest.TestCase):
    def test_threshold(self):
        self.assertEqual(streak_commands(64), ["STREAK_OFF"])
        self.assertEqual(streak_commands(65), ["STREAK_ON"])


class ModeTapReactionTests(unittest.TestCase):
    def test_mode_command_groove_and_mimic(self):
        self.assertEqual(mode_command("groove"), "MODE:GROOVE")
        self.assertEqual(mode_command("mimic"), "MODE:MIMIC")

    def test_mode_command_unknown_falls_back_to_groove(self):
        self.assertEqual(mode_command("banana"), "MODE:GROOVE")

    def test_tap_left_and_right(self):
        self.assertEqual(tap_command("L"), "TAP:L")
        self.assertEqual(tap_command("R"), "TAP:R")

    def test_reaction_commands(self):
        self.assertEqual(reaction_command("typo"), "REACT:TYPO")
        self.assertEqual(reaction_command("save"), "REACT:SAVE")
        self.assertEqual(reaction_command("groom"), "REACT:GROOM")


class IdleMilestoneTests(unittest.TestCase):
    def test_under_ten_minutes_is_silent(self):
        self.assertIsNone(idle_milestone_command(599, False, False))

    def test_ten_minutes_sends_excited_once(self):
        self.assertEqual(idle_milestone_command(600, False, False), "EXCITED")
        self.assertIsNone(idle_milestone_command(600, True, False))

    def test_twenty_minutes_sends_screensaver(self):
        self.assertEqual(idle_milestone_command(1200, True, False), "SCREENSAVER")
        self.assertIsNone(idle_milestone_command(1200, True, True))

    def test_jump_to_twenty_minutes_skips_excitement(self):
        self.assertEqual(idle_milestone_command(1200, False, False), "SCREENSAVER")


class KeystrokeTimingTests(unittest.TestCase):
    def test_40_wpm_is_about_three_keys_per_second(self):
        # 40 WPM * 5 chars / 60 s = 3.333 keys/s -> 0.3 s interval
        self.assertAlmostEqual(keystroke_interval_seconds(40), 0.3, places=3)

    def test_zero_wpm_has_no_interval(self):
        self.assertIsNone(keystroke_interval_seconds(0))


if __name__ == "__main__":
    unittest.main()
