# Bongo Cat on Linux

The cat on the little screen (the Cheap Yellow Display) is the same on
Windows, Mac, and Linux. This file is only about the program on a Linux
computer that watches your typing and talks to that screen over USB.

Linux does not have a double-click starter like the Mac. You will use a
Terminal window and paste a few commands. You do not need to know Linux
already. Copy each block as written.

------------------------------------------------------------------------
What you need

1. The Bongo Cat firmware already on the board (web flasher or Arduino
   upload of bongo_cat.ino). This file does not flash the board.

2. A USB cable that can carry data. Charge-only cables fail silently.

3. A Linux computer with a normal desktop (the screen you sit in front
   of). Logging in over SSH from another machine will not see your
   keystrokes. For that, use the testbench later in this file.

4. This project folder on disk (git clone, or Code → Download ZIP and
   unzip it).

------------------------------------------------------------------------
Open a Terminal in the project folder

A Terminal is a text window where you type commands.

- Right-click the project folder → Open in Terminal, or
- Open Terminal, then type `cd ` (with a space), drag the folder onto
  the window, and press Enter.

You should see the folder path in the prompt. Commands below assume you
are in that folder.

------------------------------------------------------------------------
One-time setup

These three blocks are only needed the first time (or after a fresh
unzip).

1. Make a private Python sandbox so packages stay in this project:

     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r bongo_cat_app/requirements_app.txt

   `venv` is a small isolated Python. `source ... activate` means "use
   that Python in this Terminal window." If you close the window, open a
   new one, `cd` back here, and run `source .venv/bin/activate` again
   before the later commands.

2. Let your user account talk to USB serial devices. Linux hides those
   from a normal account until you join the `dialout` group:

     sudo usermod -aG dialout $USER

   Type your login password when asked. Then log out of Linux entirely
   and log back in (closing Terminal is not enough). After that, you
   can use the USB board without `sudo`.

3. Plug the cat in. Check that the computer sees it:

     python3 tools/serial_smoke.py

   If that prints a port and succeeds, you are ready.

------------------------------------------------------------------------
Run the host (the program that watches typing)

In the same folder, with the sandbox still active:

  python3 bongo_cat_app/main.py --no-tray

`--no-tray` skips the small icon in the system tray. Type on this
computer. The cat should bongo. Words-per-minute prints in the Terminal.

To get the tray icon instead (sprite editor, animation settings):

  python3 bongo_cat_app/main.py

If the small cat icon never appears, typing still works. Missing tray
libraries used to crash the whole program; it now keeps running without
the icon.

Leave that window open while you type. Ctrl+C in the Terminal stops it.

------------------------------------------------------------------------
USB names, in plain language

The board shows up as a device file, usually:

  /dev/ttyUSB0    (common for CH340 / CP2102 USB chips)
  /dev/ttyACM0    (some other boards)

That path is just Linux's name for "this USB cable." If you have several
USB serial gadgets, the number might be 1 or 2 instead of 0.

If you unplug the cat while the host is running, the Terminal may print
Errno 5 / Input/output error. Leave the host running. Plug the board
back in (the name may change from ttyUSB0 to ttyUSB1). The host scans
again and reconnects. You should see "Trying to reopen USB serial..."
then Connected. You do not need to restart unless the host itself
exited.

------------------------------------------------------------------------
If serial_smoke sees no port

- Unplug and replug. Try another cable.
- In Terminal:

    dmesg | tail
    ls -l /dev/ttyUSB* /dev/ttyACM*

  `dmesg | tail` shows the last kernel messages (often "ttyUSB0" when
  you plug in). `ls` lists whether those device names exist.
- Pass the port yourself if you know it, for example:

    python3 tools/serial_smoke.py --port /dev/ttyUSB0

- If you skipped the logout after `dialout`, the port may exist but
  refuse to open. Log out and back in.

------------------------------------------------------------------------
Why typing might not reach the cat

The host reads keystrokes from the graphical desktop (X11 or Wayland:
those are Linux's names for "the thing that draws windows"). A remote
SSH session has no desktop, so it cannot feed typing.

Wayland (Ubuntu's default) does not let a normal app watch every key
the old X11 way. You do not have to log out and switch to Xorg. The
host can read the keyboard device instead.

One-time:

  sudo usermod -aG input $USER
  pip install evdev

You do not need to log out of Ubuntu. Start the host so this Terminal
has the extra permission:

  sg input -c 'python3 bongo_cat_app/main.py'

(Log out once later if you want every new Terminal to already have
that permission.)

If you are on SSH, or you just want to see the cat move without typing,
use the testbench.

------------------------------------------------------------------------
Testbench (fake typing onto the screen)

This does not pretend to type into Linux. It sends the same USB messages
the host would send, so you can watch paws, streak, and sleep.

  python3 tools/cyd_testbench.py --dry-run --demo
  python3 tools/cyd_testbench.py --demo
  python3 tools/cyd_testbench.py --wpm 80 --seconds 8
  python3 tools/cyd_testbench.py --port /dev/ttyUSB0 --wpm 20 --seconds 5

`--dry-run` prints what it would send and does not need the board.
`--demo` runs a canned sequence:

  idle → slow (15 WPM) → normal (35) → fast (55) → streak (80) → idle

Firmware stops the typing animation after about 2 seconds with no
SPEED/STOP message, so the testbench pokes the board every 1 second.

------------------------------------------------------------------------
Paw modes

From the host tray: Animation, or Settings → Behavior.

Groove (default): paws loop based on words per minute.
Mimic: one left/right tap per key. Needs this project's firmware on
the board.
Reactions (both modes): a burst on backspace (typo), a save reaction on
Ctrl+S, a short idle fidget (groom).
After 20 minutes with no keys: screensaver (sleeping cat drifts around
the display).

------------------------------------------------------------------------
Sprite studio (new cat art and screen layout)

This is a small local web editor. It does not start with the typing
host, and cloning GitHub does not start it either.

With the tray (run `main.py` without `--no-tray`):

  python3 bongo_cat_app/main.py
  # tray → Sprite editor → Start / Stop / Open in browser
  # or Settings → Sprite editor

Stop from the app kills whatever is using port 8765. Quitting the typing
host does not stop the editor.

From a Terminal instead:

  python3 tools/sprite_studio.py --no-browser

Then open the editor in a browser on this same computer. Details:
tools/sprite_studio/README.md

------------------------------------------------------------------------
Lifetime keys typed

Counted while you type. Saved at:

  ~/.config/BongoCat/keys_typed.json

`~` means your home folder (usually /home/yourname). Quitting the host
or rebooting does not reset the count.
