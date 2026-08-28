#!/usr/bin/env python3
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from port_detect import PortInfo, is_likely_esp32, select_port  # noqa: E402


class PortDetectTests(unittest.TestCase):
    def test_vid_cp2102(self):
        p = PortInfo(device="/dev/cu.SLAB_USBtoUART", vid=0x10C4, manufacturer="Silicon Labs")
        self.assertTrue(is_likely_esp32(p))

    def test_vid_ch340(self):
        p = PortInfo(device="/dev/cu.wchusbserial1410", vid=0x1A86, description="USB Serial")
        self.assertTrue(is_likely_esp32(p))

    def test_macos_path_without_vid(self):
        p = PortInfo(device="/dev/cu.usbserial-0001", description="n/a")
        self.assertTrue(is_likely_esp32(p))

    def test_usbmodem_cdc(self):
        p = PortInfo(device="/dev/cu.usbmodem1101")
        self.assertTrue(is_likely_esp32(p))

    def test_ignore_bluetooth(self):
        ports = [
            PortInfo(device="/dev/cu.Bluetooth-Incoming-Port", description="Bluetooth"),
            PortInfo(device="/dev/cu.usbserial-10", vid=0x1A86),
        ]
        chosen = select_port(ports)
        self.assertIsNotNone(chosen)
        self.assertIn("usbserial", chosen.device)

    def test_prefer_cu_over_tty(self):
        ports = [
            PortInfo(device="/dev/tty.usbserial-10", vid=0x10C4),
            PortInfo(device="/dev/cu.usbserial-10", vid=0x10C4),
        ]
        chosen = select_port(ports)
        self.assertEqual(chosen.device, "/dev/cu.usbserial-10")

    def test_empty(self):
        self.assertIsNone(select_port([]))


if __name__ == "__main__":
    unittest.main()
