#!/usr/bin/env python3
import errno
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from serial_link import (  # noqa: E402
    is_serial_drop_error,
    port_after_drop,
    should_attempt_reconnect,
)


class DropErrorTests(unittest.TestCase):
    def test_errno_5_oserror_is_unplug(self):
        self.assertTrue(is_serial_drop_error(OSError(errno.EIO, "Input/output error")))

    def test_message_from_pyserial_write_failed(self):
        exc = Exception("write failed: [Errno 5] Input/output error")
        self.assertTrue(is_serial_drop_error(exc))

    def test_timeout_is_not_unplug(self):
        self.assertFalse(is_serial_drop_error(TimeoutError("write timed out")))

    def test_permission_denied_is_not_unplug(self):
        self.assertFalse(is_serial_drop_error(OSError(errno.EACCES, "Permission denied")))


class PortAfterDropTests(unittest.TestCase):
    def test_gone_node_rescans(self):
        self.assertEqual(
            port_after_drop("/dev/ttyUSB0", ["/dev/ttyUSB1"]),
            "AUTO",
        )

    def test_same_node_still_there_keeps_path(self):
        self.assertEqual(
            port_after_drop("/dev/ttyUSB1", ["/dev/ttyUSB1"]),
            "/dev/ttyUSB1",
        )

    def test_auto_stays_auto(self):
        self.assertEqual(port_after_drop("AUTO", ["/dev/ttyUSB0"]), "AUTO")


class ReconnectScheduleTests(unittest.TestCase):
    def test_open_link_does_not_reconnect(self):
        self.assertFalse(should_attempt_reconnect(True, now=10, last_attempt=0, interval=3))

    def test_first_drop_reconnects_immediately(self):
        self.assertTrue(should_attempt_reconnect(False, now=10, last_attempt=None, interval=3))

    def test_respects_backoff(self):
        self.assertFalse(should_attempt_reconnect(False, now=11, last_attempt=10, interval=3))
        self.assertTrue(should_attempt_reconnect(False, now=13, last_attempt=10, interval=3))


if __name__ == "__main__":
    unittest.main()
