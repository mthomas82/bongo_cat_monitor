# Bongo Cat on a Mac

The official Electron DMG is unsigned. On recent macOS it often shows
"app is damaged", or it launches but never sees keystrokes. Use one of
the two hosts below instead.

Do this on Kelsey's MacBook, with the ESP32 plugged in over USB.

------------------------------------------------------------------------
Path A — Python host (no Xcode)

1. Install Python 3 from python.org if `python3 --version` fails.

2. Cheap Yellow Display boards often need a USB-serial driver:
   - CH340:  https://github.com/WCHSoftGroup/ch34xser_macos
   - CP2102: Silicon Labs CP210x VCP for Mac
   After installing, unplug and replug the board.

3. In Terminal:

   cd /path/to/bongo_cat_monitor
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r bongo_cat_app/requirements_app.txt

   python3 tools/serial_smoke.py
   # Expect a PING reply or at least the cat twitching from SPEED.

   python3 bongo_cat_app/main.py --no-tray

4. macOS will ask for Accessibility. Allow Terminal (or python3) in:
   System Settings -> Privacy & Security -> Accessibility
   and Input Monitoring. Fully quit and relaunch.

5. Type. WPM should print and the cat should bongo.

Or double-click `Start Bongo Cat.command` in this folder (same steps).

Pass a port if auto-detect misses it:

   python3 bongo_cat_app/main.py --no-tray --port /dev/cu.usbserial-0001

List devices:  ls /dev/cu.usb*

------------------------------------------------------------------------
Path B — Native menu-bar app (best once it builds)

Needs Rust (rustup.rs) and Xcode Command Line Tools:

   xcode-select --install
   cd bongo-cat-macos
   make
   make run

That produces build/BongoCat.app (ad-hoc signed). If Gatekeeper
complains:

   xattr -cr bongo-cat-macos/build/BongoCat.app
   open bongo-cat-macos/build/BongoCat.app

Grant Accessibility to "Bongo Cat", then restart the app.

This client is the one multiple Mac users confirmed works for WPM.
Source: Dalton Rooney, vendored in bongo-cat-macos/ (see THIRD_PARTY.md).
The Makefile targets the Mac you build on (Intel or Apple Silicon).

------------------------------------------------------------------------
Do not use for now

- GitHub Releases DMG from vostoklabs (unsigned Electron)
- sudo open /Applications/Bongo\\ Cat.app  (does not fix TCC)

------------------------------------------------------------------------
Sprite studio (new cat art + screen layout)

Does not start with the Python host. Run without --no-tray, then:

  tray → Sprite editor → Start / Stop / Open in browser
  Settings → Sprite editor

Or:  python3 tools/sprite_studio.py --no-browser

Details: tools/sprite_studio/README.md

------------------------------------------------------------------------
If serial_smoke.py sees no port

- Try another USB cable (charge-only cables fail)
- Install CH340/CP2102 driver, reboot
- ls /dev/cu.*  and pass --port
- The board must already have bongo_cat.ino (or the web flasher) on it
