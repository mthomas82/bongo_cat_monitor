#!/usr/bin/env python3
"""Linux keyboard backends: pynput on X11, evdev on Wayland."""

from __future__ import annotations

import os
import select
import sys

WAYLAND_HELP = """
Wayland blocks the old X11 key listener, so the host reads the keyboard
device instead. You do not need to log out to Xorg.

One-time:
  sudo usermod -aG input $USER

Then start the host in a terminal that already has that group (no desktop
logout required):

  cd ~/bongo_cat_monitor
  source .venv/bin/activate
  sg input -c 'python3 bongo_cat_app/main.py'
"""


class EvdevKey:
    def __init__(self, name: str, char: str | None = None) -> None:
        self.name = name
        self.char = char

    def __str__(self) -> str:
        if self.char is not None:
            return repr(self.char)
        return f"Key.{self.name}"


_SPECIAL = {
    "KEY_SPACE": "space",
    "KEY_ENTER": "enter",
    "KEY_KPENTER": "enter",
    "KEY_BACKSPACE": "backspace",
    "KEY_DELETE": "delete",
    "KEY_ESC": "esc",
    "KEY_TAB": "tab",
    "KEY_LEFTCTRL": "ctrl_l",
    "KEY_RIGHTCTRL": "ctrl_r",
    "KEY_LEFTSHIFT": "shift",
    "KEY_RIGHTSHIFT": "shift_r",
    "KEY_LEFTALT": "alt_l",
    "KEY_RIGHTALT": "alt_r",
    "KEY_LEFTMETA": "cmd",
    "KEY_RIGHTMETA": "cmd_r",
    "KEY_UP": "up",
    "KEY_DOWN": "down",
    "KEY_LEFT": "left",
    "KEY_RIGHT": "right",
    "KEY_HOME": "home",
    "KEY_END": "end",
    "KEY_PAGEUP": "page_up",
    "KEY_PAGEDOWN": "page_down",
    "KEY_INSERT": "insert",
    "KEY_CAPSLOCK": "caps_lock",
}

_SHIFT_CHARS = {
    "KEY_MINUS": "-",
    "KEY_EQUAL": "=",
    "KEY_LEFTBRACE": "[",
    "KEY_RIGHTBRACE": "]",
    "KEY_SEMICOLON": ";",
    "KEY_APOSTROPHE": "'",
    "KEY_GRAVE": "`",
    "KEY_BACKSLASH": "\\",
    "KEY_COMMA": ",",
    "KEY_DOT": ".",
    "KEY_SLASH": "/",
}


def keyboard_backend(environ=None) -> str:
    env = os.environ if environ is None else environ
    session = str(env.get("XDG_SESSION_TYPE", "")).lower()
    if session == "wayland":
        return "evdev"
    return "pynput"


def key_from_evdev_name(code_name: str):
    if not code_name:
        return None
    if code_name in _SPECIAL:
        return EvdevKey(_SPECIAL[code_name])
    if code_name.startswith("KEY_") and len(code_name) == 5:
        ch = code_name[-1]
        if ch.isalpha():
            return EvdevKey(ch.lower(), ch.lower())
        if ch.isdigit():
            return EvdevKey(ch, ch)
    if code_name in _SHIFT_CHARS:
        ch = _SHIFT_CHARS[code_name]
        return EvdevKey(ch, ch)
    if code_name.startswith("KEY_F") and code_name[5:].isdigit():
        return EvdevKey(code_name[4:].lower())
    return None


def dispatch_key_event(code_name, value, on_press, on_release) -> bool:
    if value == 2:
        return False
    key = key_from_evdev_name(code_name)
    if key is None:
        return False
    if value == 1:
        on_press(key)
        return True
    if value == 0:
        on_release(key)
        return True
    return False


def _code_name(evdev_ecodes, code) -> str:
    name = evdev_ecodes.keys.get(code)
    if isinstance(name, (list, tuple)):
        name = name[0] if name else None
    return name or ""


def open_keyboards(list_devices, input_device_cls, ev_key, key_a):
    devices = []
    for path in list_devices():
        try:
            dev = input_device_cls(path)
        except OSError:
            continue
        try:
            caps = dev.capabilities()
        except OSError:
            continue
        keys = caps.get(ev_key) or []
        if key_a in keys:
            devices.append(dev)
    return devices


def _listen_evdev(on_press, on_release) -> None:
    from evdev import InputDevice, ecodes, list_devices

    devices = open_keyboards(list_devices, InputDevice, ecodes.EV_KEY, ecodes.KEY_A)
    if not devices:
        raise PermissionError("no readable keyboard devices")
    print(f"Wayland: listening on {len(devices)} keyboard device(s) via evdev")
    fds = {dev.fd: dev for dev in devices}
    try:
        while True:
            ready, _, _ = select.select(list(fds), [], [], 0.5)
            for fd in ready:
                dev = fds[fd]
                for event in dev.read():
                    if event.type != ecodes.EV_KEY:
                        continue
                    dispatch_key_event(
                        _code_name(ecodes, event.code),
                        event.value,
                        on_press,
                        on_release,
                    )
    except KeyboardInterrupt:
        pass
    finally:
        for dev in devices:
            try:
                dev.close()
            except OSError:
                pass


def run_linux_keyboard(on_press, on_release, environ=None) -> str:
    """Block until Ctrl+C. Returns the backend that actually ran."""
    backend = keyboard_backend(environ)
    if backend == "evdev":
        try:
            _listen_evdev(on_press, on_release)
            return "evdev"
        except ImportError:
            print("Wayland needs the evdev package:")
            print("  pip install evdev")
            print(WAYLAND_HELP)
        except (PermissionError, OSError) as exc:
            print(f"Wayland keyboard devices are not readable ({exc}).")
            print(WAYLAND_HELP)
        print("Trying the X11 listener anyway (only some windows will work).")

    from pynput import keyboard

    try:
        with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
            listener.join()
    except KeyboardInterrupt:
        pass
    return "pynput"


if __name__ == "__main__":
    print(keyboard_backend(), file=sys.stderr)
