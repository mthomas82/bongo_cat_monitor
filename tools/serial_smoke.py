#!/usr/bin/env python3
"""Talk to a Bongo Cat ESP32 without keyboard monitoring.

Usage (from repo root, venv with pyserial):
  python3 tools/serial_smoke.py
  python3 tools/serial_smoke.py --port /dev/cu.usbserial-0001
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

from port_detect import find_esp32_device, list_system_ports  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Bongo Cat serial smoke test")
    parser.add_argument("--port", default="AUTO")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    print("Ports seen:")
    ports = list_system_ports()
    if not ports:
        print("  (none)")
    for p in ports:
        print(f"  {p.device:40} vid={p.vid!s:6} {p.description} [{p.manufacturer}]")

    device = find_esp32_device(args.port)
    if not device:
        print("No ESP32-like port found. Plug the board in, install the CH340/CP2102")
        print("driver if needed, and pass --port /dev/cu.usbserial-XXXX")
        return 2

    print(f"Opening {device} @ {args.baud}")
    try:
        import serial
    except ImportError:
        print("pyserial is missing. pip install pyserial")
        return 2

    ser = serial.Serial(device, args.baud, timeout=1)
    time.sleep(2.0)  # ESP32 resets on open
    ser.reset_input_buffer()

    def send(cmd: str) -> str:
        ser.write((cmd.strip() + "\n").encode("ascii"))
        ser.flush()
        time.sleep(0.15)
        chunks = []
        while ser.in_waiting:
            chunks.append(ser.readline().decode("utf-8", errors="replace").strip())
        return " | ".join(chunks)

    pong = send("PING")
    print(f"PING -> {pong or '(no reply; some firmware still animates)'}")
    print("STATS ->", send("STATS:CPU:12,RAM:34,WPM:56") or "(no reply)")
    print("TIME  ->", send("TIME:12:34") or "(no reply)")
    print("SPEED ->", send("SPEED:120") or "(no reply)")
    time.sleep(1.5)
    print("STOP  ->", send("STOP") or "(no reply)")
    ser.close()
    print("Done. If the cat twitched, serial is good; remaining Mac issues are key permissions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
