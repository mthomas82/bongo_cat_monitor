#!/usr/bin/env python3
"""CYD testbench — spoof typing over USB serial (or print commands).

This does not generate OS key events. It talks the Bongo Cat protocol so
you can watch paws / streak / sleep on the Cheap Yellow Display.

Examples:
  python3 tools/cyd_testbench.py --dry-run --demo
  python3 tools/cyd_testbench.py --demo
  python3 tools/cyd_testbench.py --wpm 80 --seconds 6
  python3 tools/cyd_testbench.py --port /dev/ttyUSB0 --wpm 20 --seconds 5
"""

from __future__ import annotations

import argparse
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "bongo_cat_app")
if APP not in sys.path:
    sys.path.insert(0, APP)

from fake_typist import DEMO_PHASES, ListSink, play_session, virtual_clock  # noqa: E402
from port_detect import find_esp32_device  # noqa: E402
from protocol import wpm_to_speed_ms  # noqa: E402


class PrintSink(ListSink):
    def send(self, command: str) -> None:
        super().send(command)
        print(f"  -> {command}")


class SerialSink:
    def __init__(self, port, baud: int = 115200) -> None:
        import serial

        print(f"Opening {port} @ {baud} (board will reset for ~2s)")
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2.0)
        self.ser.reset_input_buffer()

    def send(self, command: str) -> None:
        line = command.strip() + "\n"
        self.ser.write(line.encode("ascii"))
        self.ser.flush()
        print(f"  -> {command}")
        time.sleep(0.05)
        bits = []
        while self.ser.in_waiting:
            bits.append(self.ser.readline().decode("utf-8", errors="replace").strip())
        if bits:
            print(f"     CYD: {' | '.join(bits)}")

    def close(self) -> None:
        try:
            self.ser.close()
        except Exception:
            pass


def play_demo(sink, now=time.monotonic, sleep=time.sleep) -> None:
    for name, duration, wpm in DEMO_PHASES:
        extra = ""
        if wpm > 0:
            extra = f" SPEED:{wpm_to_speed_ms(wpm)}ms"
        print(f"\n=== {name}  wpm={wpm}  {duration:.0f}s{extra} ===")
        play_session(sink, wpm=wpm, duration_s=duration, now=now, sleep=sleep)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Spoof Bongo Cat typing on a Cheap Yellow Display"
    )
    parser.add_argument("--port", default="AUTO", help="Serial device, or AUTO")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--dry-run", action="store_true", help="Print commands, no serial")
    parser.add_argument("--demo", action="store_true", help="Idle → slow → normal → fast → streak → idle")
    parser.add_argument("--wpm", type=float, default=None, help="Hold this WPM")
    parser.add_argument("--seconds", type=float, default=8.0, help="Duration for --wpm")
    args = parser.parse_args()

    if not args.demo and args.wpm is None:
        args.demo = True

    clock = {}
    if args.dry_run:
        sink = PrintSink()
        now, sleep = virtual_clock()
        clock = {"now": now, "sleep": sleep}
        print("Dry-run: nothing sent to hardware (instant)")
    else:
        device = find_esp32_device(args.port)
        if not device:
            print("No ESP32-like port. Pass --port /dev/ttyUSB0 (Linux)")
            print("or /dev/cu.usbserial-* (Mac). Use --dry-run to see commands.")
            if sys.platform.startswith("linux"):
                print("If the device exists but open fails: sudo usermod -aG dialout $USER && log out.")
            return 2
        try:
            sink = SerialSink(device, args.baud)
        except Exception as exc:
            print(f"Could not open {device}: {exc}")
            if sys.platform.startswith("linux"):
                print("Likely permissions: sudo usermod -aG dialout $USER")
                print("then log out and back in. Check: ls -l /dev/ttyUSB* /dev/ttyACM*")
            return 2
        sink.send("PING")

    try:
        if args.demo:
            play_demo(sink, **clock)
        else:
            print(f"\n=== hold wpm={args.wpm} for {args.seconds}s ===")
            play_session(sink, wpm=args.wpm, duration_s=args.seconds, **clock)
        print("\nDone.")
        return 0
    finally:
        close = getattr(sink, "close", None)
        if close:
            close()


if __name__ == "__main__":
    sys.exit(main())
