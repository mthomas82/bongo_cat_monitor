# Bongo Cat on a Mac

You do not need Terminal, Python knowledge, or Xcode.

------------------------------------------------------------------------
Do this

1. Plug the cat into the Mac with a USB data cable (charge-only cables fail).

2. Get the project folder
   - Easiest: unzip a download of this repo (Code → Download ZIP), or
   - If we published a release: download BongoCat-macOS.zip, unzip it,
     then skip to step 4 and open BongoCat.app instead.

3. Double-click  Start Bongo Cat.command
   First time, macOS may say it cannot be opened. Right-click the file →
   Open → Open. That is a one-time Gatekeeper click.

4. Follow the two pop-ups
   - If Python is missing, click Get Python, install it (keep the
     default checkbox that says "Add Python to PATH"), then double-click
     Start Bongo Cat.command again.
   - Allow Accessibility and Input Monitoring for Terminal (or python3).
     Quit and start once more if the cat does not react to typing.

5. Type. The cat should bongo. WPM prints in the Terminal window.

Keep Start Bongo Cat.command inside the unzipped folder. Later you only
repeat step 3.

------------------------------------------------------------------------
If the cat does not move

- Try another USB cable, then unplug and replug.
- In the first-run dialog choose Driver help (CH340 is the usual chip).
- The board must already have the Bongo Cat firmware (web flasher or
  Arduino upload of bongo_cat.ino).

------------------------------------------------------------------------
Lifetime keys typed

Counted while you type. Saved at
~/Library/Application Support/BongoCat/keys_typed.json
so quitting or restarting the Mac does not reset it.

------------------------------------------------------------------------
Optional: native menu-bar app

If you have a BongoCat.app from GitHub Releases, right-click → Open,
grant Accessibility to "Bongo Cat", and leave it in the menu bar.

Building that app yourself needs Rust + Xcode Command Line Tools:

  xcode-select --install
  cd bongo-cat-macos && make && make run

Do not use the old unsigned Electron DMG from vostoklabs. It often
shows "app is damaged" or never sees keystrokes.
