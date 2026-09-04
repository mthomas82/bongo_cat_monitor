#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from key_count import is_countable_key  # noqa: E402
from linux_keys import (  # noqa: E402
    dispatch_key_event,
    key_from_evdev_name,
    keyboard_backend,
)
from mimic import MimicController  # noqa: E402


class BackendChoiceTests(unittest.TestCase):
    def test_wayland_uses_evdev(self):
        self.assertEqual(keyboard_backend({"XDG_SESSION_TYPE": "wayland"}), "evdev")

    def test_x11_uses_pynput(self):
        self.assertEqual(keyboard_backend({"XDG_SESSION_TYPE": "x11"}), "pynput")


class EvdevKeyMappingTests(unittest.TestCase):
    def test_letter_matches_pynput_style(self):
        key = key_from_evdev_name("KEY_A")
        self.assertEqual(str(key), "'a'")
        self.assertTrue(is_countable_key(key))

    def test_s_key_triggers_save_with_ctrl(self):
        c = MimicController(mode="groove")
        ctrl = key_from_evdev_name("KEY_LEFTCTRL")
        s = key_from_evdev_name("KEY_S")
        c.on_press(ctrl, 0.0)
        self.assertEqual(c.on_press(s, 0.01), ["REACT:SAVE"])

    def test_backspace_is_erase(self):
        c = MimicController(mode="groove")
        bs = key_from_evdev_name("KEY_BACKSPACE")
        now = 0.0
        cmds = []
        for i in range(4):
            cmds.extend(c.on_press(bs, now + i * 0.1))
            c.on_release(bs, now + i * 0.1 + 0.01)
        self.assertIn("REACT:TYPO", cmds)

    def test_ctrl_is_not_countable(self):
        self.assertFalse(is_countable_key(key_from_evdev_name("KEY_LEFTCTRL")))


class DispatchTests(unittest.TestCase):
    def test_press_and_release(self):
        presses, releases = [], []
        self.assertTrue(dispatch_key_event("KEY_A", 1, presses.append, releases.append))
        self.assertTrue(dispatch_key_event("KEY_A", 0, presses.append, releases.append))
        self.assertEqual(str(presses[0]), "'a'")
        self.assertEqual(str(releases[0]), "'a'")

    def test_kernel_repeat_is_ignored(self):
        presses = []
        self.assertFalse(dispatch_key_event("KEY_A", 2, presses.append, lambda k: None))
        self.assertEqual(presses, [])


if __name__ == "__main__":
    unittest.main()
