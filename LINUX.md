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

These blocks are only needed the first time (or after a fresh unzip).

1. Make a private Python sandbox so packages stay in this project:

     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r bongo_cat_app/requirements_app.txt

   `venv` is a small isolated Python. `source ... activate` means "use
   that Python in this Terminal window." If you close the window, open a
   new one, `cd` back here, and run `source .venv/bin/activate` again
   before the later commands.

2. Let your account talk to the USB board (`dialout`) and read the
   keyboard (`input`):

     sudo usermod -aG dialout $USER
     sudo usermod -aG input $USER

   Type your login password when asked (or use the fingerprint reader).

   `dialout` needs a full log out of Linux and back in once (closing
   Terminal is not enough). After that, USB works without `sudo`.

   `input` does not need a logout if you start the host with `sg input`
   as shown below.

3. Plug the cat in. Check that the computer sees it:

     python3 tools/serial_smoke.py

   If that prints a port and succeeds, you are ready.

------------------------------------------------------------------------
Start the host (every time)

Ubuntu's default desktop is Wayland. A normal app is not allowed to
watch every key the old X11 way, so this program reads the keyboard
device instead. You do not log out and switch to Xorg.

In the project folder, with the sandbox active:

  source .venv/bin/activate
  sg input -c 'python3 bongo_cat_app/main.py'

The flag is a lowercase `-c`. Uppercase `-C` is invalid and `sg` will
refuse to start.

Leave that window open. You want a line like `Connected to ... /dev/ttyUSB0`
(the number may be 1 or 2). Then type anywhere — Discord, a browser, or
even this Terminal. Success looks like `Typing started`.

Ctrl+C in that Terminal stops it.

The small cat icon in the task bar may never appear. Typing still works.
Sprite editor without the icon:

  python3 tools/sprite_studio.py --no-browser

To skip the tray on purpose:

  sg input -c 'python3 bongo_cat_app/main.py --no-tray'

If you already logged out once after joining `input`, every new Terminal
has that permission and you can run `python3 bongo_cat_app/main.py`
without `sg`. Until then, keep using `sg input -c`.

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
  you plug in). `ls` lists whether those device names exist. On some
  laptops `dmesg` needs `sudo dmesg | tail`.
- Pass the port yourself if you know it, for example:

    python3 tools/serial_smoke.py --port /dev/ttyUSB0

- If you skipped the logout after `dialout`, the port may exist but
  refuse to open. Log out and back in.
- Run smoke and the host from the project folder, not from `~` (your
  home folder), or the script will not be found.

------------------------------------------------------------------------
If the cat does not move when you type

- Confirm the host window still says Connected, then that Typing started
  appears when you press keys.
- If there is no Connected line, USB is not talking. Ctrl+C the host
  and use the testbench below.
- If you started without `sg input -c` on Wayland, keys will not be
  seen. Stop it and start again with the command in "Start the host".
- SSH from another machine cannot feed typing. Use the testbench.

------------------------------------------------------------------------
Testbench (fake typing onto the screen)

This does not pretend to type into Linux. It sends the same USB messages
the host would send, so you can watch paws, streak, and sleep.

Stop the typing host first (only one program may own the USB port).

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

From the host tray: Animation, or Settings → Behavior. If there is no
tray icon, Mimic still needs a settings window or a firmware default;
Groove is the default.

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

If the tray icon is present: tray → Sprite editor → Start / Stop /
Open in browser, or Settings → Sprite editor.

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
