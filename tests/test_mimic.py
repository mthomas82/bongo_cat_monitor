#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from mimic import MimicController  # noqa: E402


class FakeKey:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class MimicTapTests(unittest.TestCase):
    def test_mimic_alternates_paws_and_ignores_repeat(self):
        c = MimicController(mode="mimic")
        a = FakeKey("'a'")
        self.assertEqual(c.on_press(a, 0.0), ["TAP:L"])
        self.assertEqual(c.on_press(a, 0.01), [])  # OS repeat
        c.on_release(a, 0.02)
        b = FakeKey("'b'")
        self.assertEqual(c.on_press(b, 0.03), ["TAP:R"])
        self.assertEqual(c.on_press(FakeKey("'c'"), 0.04), ["TAP:L"])

    def test_groove_mode_does_not_tap(self):
        c = MimicController(mode="groove")
        self.assertEqual(c.on_press(FakeKey("'a'"), 0.0), [])

    def test_modifiers_do_not_tap(self):
        c = MimicController(mode="mimic")
        self.assertEqual(c.on_press(FakeKey("Key.ctrl"), 0.0), [])
        self.assertEqual(c.on_press(FakeKey("Key.cmd"), 0.0), [])

    def test_set_mode_emits_firmware_command(self):
        c = MimicController(mode="groove")
        self.assertEqual(c.set_mode("mimic"), ["MODE:MIMIC"])
        self.assertEqual(c.mode, "mimic")
        self.assertEqual(c.set_mode("groove"), ["MODE:GROOVE"])


class TypoReactionTests(unittest.TestCase):
    def test_four_backspaces_in_window_fires_typo(self):
        c = MimicController(mode="groove")
        bs = FakeKey("Key.backspace")
        cmds = []
        for i, t in enumerate((0.0, 0.2, 0.4, 0.6)):
            cmds.extend(c.on_press(bs, t))
            c.on_release(bs, t + 0.05)
        self.assertIn("REACT:TYPO", cmds)

    def test_three_backspaces_do_not_fire(self):
        c = MimicController(mode="groove")
        bs = FakeKey("Key.backspace")
        cmds = []
        for t in (0.0, 0.2, 0.4):
            cmds.extend(c.on_press(bs, t))
            c.on_release(bs, t + 0.05)
        self.assertNotIn("REACT:TYPO", cmds)

    def test_typo_cooldown_suppresses_immediate_retrigger(self):
        c = MimicController(mode="groove")
        bs = FakeKey("Key.backspace")
        for t in (0.0, 0.1, 0.2, 0.3):
            c.on_press(bs, t)
            c.on_release(bs, t + 0.02)
        cmds = []
        for t in (0.4, 0.5, 0.6, 0.7):
            cmds.extend(c.on_press(bs, t))
            c.on_release(bs, t + 0.02)
        self.assertNotIn("REACT:TYPO", cmds)


class SaveReactionTests(unittest.TestCase):
    def test_ctrl_s_fires_save(self):
        c = MimicController(mode="groove")
        c.on_press(FakeKey("Key.ctrl"), 0.0)
        cmds = c.on_press(FakeKey("'s'"), 0.01)
        self.assertIn("REACT:SAVE", cmds)

    def test_cmd_s_fires_save(self):
        c = MimicController(mode="groove")
        c.on_press(FakeKey("Key.cmd"), 0.0)
        cmds = c.on_press(FakeKey("'s'"), 0.01)
        self.assertIn("REACT:SAVE", cmds)

    def test_s_alone_does_not_save(self):
        c = MimicController(mode="groove")
        self.assertNotIn("REACT:SAVE", c.on_press(FakeKey("'s'"), 0.0))


class GroomReactionTests(unittest.TestCase):
    def test_groom_fires_once_in_idle_window(self):
        c = MimicController(mode="groove")
        c.on_press(FakeKey("'a'"), 0.0)
        c.on_release(FakeKey("'a'"), 0.1)
        c.on_typing_idle(1.0)
        self.assertEqual(c.poll(3.6), ["REACT:GROOM"])
        self.assertEqual(c.poll(4.0), [])

    def test_groom_cancelled_if_typing_resumes(self):
        c = MimicController(mode="groove")
        c.on_typing_idle(0.0)
        c.on_press(FakeKey("'a'"), 1.0)
        self.assertEqual(c.poll(3.0), [])

    def test_groom_missed_after_window(self):
        c = MimicController(mode="groove")
        c.on_typing_idle(0.0)
        self.assertEqual(c.poll(9.0), [])
        self.assertEqual(c.poll(9.5), [])


if __name__ == "__main__":
    unittest.main()
