# Bongo Cat on Linux

The Cheap Yellow Display firmware is the same on every OS. This file is
the desktop Python host on Linux.

------------------------------------------------------------------------
Run the host

  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r bongo_cat_app/requirements_app.txt

  python3 tools/serial_smoke.py
  python3 bongo_cat_app/main.py --no-tray

Serial
  Device is usually /dev/ttyUSB0 (CH340/CP2102) or /dev/ttyACM0.
  You must be in group dialout:

    sudo usermod -aG dialout $USER
    # log out and back in

Real typing needs a graphical session (X11/Wayland). Headless SSH will
not feed pynput. Use the testbench instead.

------------------------------------------------------------------------
Testbench (spoof typing onto the CYD)

Does not fake OS keystrokes. It sends the same serial commands the host
would send, so you can watch paws / streak / sleep without typing.

  python3 tools/cyd_testbench.py --dry-run --demo
  python3 tools/cyd_testbench.py --demo
  python3 tools/cyd_testbench.py --wpm 80 --seconds 8
  python3 tools/cyd_testbench.py --port /dev/ttyUSB0 --wpm 20 --seconds 5

Demo phases: idle → slow (15) → normal (35) → fast (55) → streak (80) → idle.

Firmware stops typing animation after ~2s without SPEED/STOP, so the
testbench keepalives every 1s.

------------------------------------------------------------------------
If serial_smoke sees no port

  dmesg | tail
  ls -l /dev/ttyUSB* /dev/ttyACM*
  try another cable
  pass --port explicitly
