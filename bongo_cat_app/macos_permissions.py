"""macOS Accessibility helpers for pynput / rdev keyboard monitoring."""

from __future__ import annotations

import ctypes
import sys
from typing import Optional

PERMISSION_HELP = """
macOS must grant this app Accessibility (and usually Input Monitoring)
or it cannot see keystrokes — the cat will idle forever.

System Settings -> Privacy & Security -> Accessibility
  - enable Terminal, python3, or "Bongo Cat" (whichever you launched)

System Settings -> Privacy & Security -> Input Monitoring
  - enable the same program

Then fully quit and relaunch this app.

If you downloaded an .app and macOS says it is damaged:
  xattr -cr /Applications/Bongo\\ Cat.app
"""


def _ax_lib() -> Optional[ctypes.CDLL]:
    if sys.platform != "darwin":
        return None
    path = "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
    try:
        return ctypes.cdll.LoadLibrary(path)
    except OSError:
        return None


def is_accessibility_trusted() -> bool:
    if sys.platform != "darwin":
        return True
    lib = _ax_lib()
    if lib is None:
        return True
    try:
        lib.AXIsProcessTrusted.restype = ctypes.c_bool
        lib.AXIsProcessTrusted.argtypes = []
        return bool(lib.AXIsProcessTrusted())
    except Exception:
        return True


def prompt_accessibility() -> bool:
    """Return current trust state; on macOS also request the system prompt."""
    if sys.platform != "darwin":
        return True
    lib = _ax_lib()
    if lib is None:
        return True
    try:
        cf = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        # AXIsProcessTrustedWithOptions(CFDictionaryRef) — pass NULL to only check,
        # or a dict with kAXTrustedCheckOptionPrompt=true.
        # Simplest portable prompt: call with a dummy; if that fails, still print help.
        lib.AXIsProcessTrustedWithOptions.restype = ctypes.c_bool
        lib.AXIsProcessTrustedWithOptions.argtypes = [ctypes.c_void_p]
        # NULL skips the prompt; use CFDict if we can. Fall back to check-only.
        trusted = bool(lib.AXIsProcessTrusted())
        if not trusted:
            # Build {kAXTrustedCheckOptionPrompt: true}
            kCFBooleanTrue = ctypes.c_void_p.in_dll(cf, "kCFBooleanTrue")
            prompt_key = ctypes.c_void_p.in_dll(lib, "kAXTrustedCheckOptionPrompt")
            cf.CFDictionaryCreate.restype = ctypes.c_void_p
            keys = (ctypes.c_void_p * 1)(prompt_key)
            vals = (ctypes.c_void_p * 1)(kCFBooleanTrue)
            # Use default allocators (NULL)
            d = cf.CFDictionaryCreate(None, keys, vals, 1, None, None)
            lib.AXIsProcessTrustedWithOptions(d)
        return is_accessibility_trusted()
    except Exception:
        return is_accessibility_trusted()


def warn_if_untrusted() -> bool:
    """Print setup help when Accessibility is off. Returns True if OK to listen."""
    if sys.platform != "darwin":
        return True
    if is_accessibility_trusted():
        return True
    print(PERMISSION_HELP.strip())
    prompt_accessibility()
    if is_accessibility_trusted():
        return True
    print("Waiting will not help until you flip the Accessibility toggle and relaunch.")
    return False
