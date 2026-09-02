#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from key_count import KeyCounter, is_countable_key  # noqa: E402
from protocol import stats_command  # noqa: E402


class FakeKey:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class CountableKeyTests(unittest.TestCase):
    def test_letters_and_space_count(self):
        self.assertTrue(is_countable_key(FakeKey("'a'")))
        self.assertTrue(is_countable_key(FakeKey("Key.space")))
        self.assertTrue(is_countable_key(FakeKey("Key.enter")))
        self.assertTrue(is_countable_key(FakeKey("Key.backspace")))

    def test_modifiers_do_not_count(self):
        self.assertFalse(is_countable_key(FakeKey("Key.ctrl")))
        self.assertFalse(is_countable_key(FakeKey("Key.cmd")))
        self.assertFalse(is_countable_key(FakeKey("Key.alt")))
        self.assertFalse(is_countable_key(FakeKey("Key.shift")))
        self.assertFalse(is_countable_key(FakeKey("Key.caps_lock")))

    def test_function_and_arrows_do_not_count(self):
        self.assertFalse(is_countable_key(FakeKey("Key.f1")))
        self.assertFalse(is_countable_key(FakeKey("Key.up")))
        self.assertFalse(is_countable_key(FakeKey("Key.page_down")))


class KeyCounterPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "keys_typed.json"
        self.clock = [1000.0]

        def now():
            return self.clock[0]

        self.now = now

    def tearDown(self):
        self.tmp.cleanup()

    def test_starts_at_zero_when_file_missing(self):
        c = KeyCounter(self.path, now=self.now)
        self.assertEqual(c.total, 0)
        self.assertFalse(self.path.exists())

    def test_add_increments_in_memory(self):
        c = KeyCounter(self.path, now=self.now)
        self.assertEqual(c.add(1), 1)
        self.assertEqual(c.add(4), 5)
        self.assertEqual(c.total, 5)

    def test_flush_then_new_instance_restores_total(self):
        c = KeyCounter(self.path, now=self.now)
        c.add(12)
        c.flush()
        self.assertTrue(self.path.exists())
        reloaded = KeyCounter(self.path, now=self.now)
        self.assertEqual(reloaded.total, 12)

    def test_survives_reopen_without_explicit_flush_after_interval(self):
        c = KeyCounter(self.path, now=self.now, min_save_interval_s=2.0)
        c.add(3)
        self.assertFalse(self.path.exists())
        self.clock[0] += 2.0
        self.assertTrue(c.maybe_flush())
        reloaded = KeyCounter(self.path, now=self.now)
        self.assertEqual(reloaded.total, 3)

    def test_maybe_flush_does_not_write_before_interval(self):
        c = KeyCounter(self.path, now=self.now, min_save_interval_s=2.0)
        c.add(1)
        self.clock[0] += 0.5
        self.assertFalse(c.maybe_flush())
        self.assertFalse(self.path.exists())

    def test_corrupt_file_starts_at_zero(self):
        self.path.write_text("{not json", encoding="utf-8")
        c = KeyCounter(self.path, now=self.now)
        self.assertEqual(c.total, 0)

    def test_negative_or_missing_count_is_zero(self):
        self.path.write_text('{"keys_typed": -9}', encoding="utf-8")
        self.assertEqual(KeyCounter(self.path, now=self.now).total, 0)

    def test_flush_is_durable_json(self):
        c = KeyCounter(self.path, now=self.now)
        c.add(7)
        c.flush()
        text = self.path.read_text(encoding="utf-8")
        self.assertIn('"keys_typed"', text)
        self.assertIn("7", text)


class EngineCountsKeysTests(unittest.TestCase):
    def test_engine_counts_presses_ignores_repeat_and_modifiers(self):
        try:
            from engine import BongoCatEngine
        except ImportError:
            self.skipTest("engine extra deps (pynput/serial) not installed")

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "keys_typed.json"
        engine = BongoCatEngine()
        engine.key_counter = KeyCounter(path, now=lambda: 0.0)

        class K:
            def __init__(self, name):
                self.name = name

            def __str__(self):
                return self.name

        a = K("'a'")
        engine.on_key_press(a)
        engine.on_key_press(a)
        self.assertEqual(engine.key_counter.total, 1)
        engine.on_key_release(a)
        engine.on_key_press(K("'b'"))
        self.assertEqual(engine.key_counter.total, 2)
        engine.on_key_press(K("Key.shift"))
        self.assertEqual(engine.key_counter.total, 2)
        engine.key_counter.flush()
        self.assertEqual(KeyCounter(path).total, 2)


class StatsCommandKeysTests(unittest.TestCase):
    def test_stats_without_keys_keeps_old_shape(self):
        self.assertEqual(stats_command(10, 20, 0), "STATS:CPU:10,RAM:20,WPM:0")

    def test_stats_appends_keys(self):
        self.assertEqual(
            stats_command(1, 2, 80, keys=12345),
            "STATS:CPU:1,RAM:2,WPM:80,KEYS:12345",
        )


if __name__ == "__main__":
    unittest.main()
