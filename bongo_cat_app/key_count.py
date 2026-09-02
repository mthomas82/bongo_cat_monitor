"""Lifetime keys-typed counter with durable on-disk persistence.

The count lives in a JSON file under the OS app-data directory so quitting
the host or rebooting the Mac does not reset it. Writes are atomic and
fsync'd so a hard power cut does not leave a truncated file.
"""

from __future__ import annotations

import json
import os
import platform
import re
from pathlib import Path
from typing import Callable, Optional


_MODIFIER = re.compile(
    r"(ctrl|cmd|alt|shift|caps_lock|caps lock)",
    re.IGNORECASE,
)
_FUNCTION = re.compile(r"(^|\.)f([1-9]|1[0-2])(\b|$)", re.IGNORECASE)


def default_data_dir() -> Path:
    home = Path.home()
    system = platform.system()
    if system == "Darwin":
        return home / "Library" / "Application Support" / "BongoCat"
    if system == "Windows":
        return home / "AppData" / "Roaming" / "BongoCat"
    return home / ".config" / "BongoCat"


def default_path() -> Path:
    return default_data_dir() / "keys_typed.json"


def is_countable_key(key) -> bool:
    """True for typing keys (letters, digits, space, enter, backspace, etc.)."""
    s = str(key).lower()
    if _MODIFIER.search(s):
        return False
    if _FUNCTION.search(s):
        return False
    if any(
        token in s
        for token in (
            "page_up",
            "page_down",
            "pageup",
            "pagedown",
            "insert",
        )
    ):
        return False
    # Arrows: Key.up / Key.down / Key.left / Key.right — not "shift" leftovers
    if s in (
        "key.up",
        "key.down",
        "key.left",
        "key.right",
        "key.home",
        "key.end",
        "up",
        "down",
        "left",
        "right",
        "home",
        "end",
    ):
        return False
    return True


def _read_total(path: Path) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0
    if not isinstance(data, dict):
        return 0
    raw = data.get("keys_typed", 0)
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 0
    return n if n > 0 else 0


def _atomic_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    blob = json.dumps(payload, indent=2) + "\n"
    data = blob.encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(str(tmp), flags, 0o644)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(str(tmp), str(path))
    try:
        dirfd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except OSError:
        pass


class KeyCounter:
    def __init__(
        self,
        path: Optional[Path] = None,
        now: Optional[Callable[[], float]] = None,
        min_save_interval_s: float = 2.0,
    ) -> None:
        self.path = Path(path) if path is not None else default_path()
        self._now = now
        self.min_save_interval_s = float(min_save_interval_s)
        self._total = _read_total(self.path) if self.path.exists() else 0
        self._dirty = False
        self._last_save = self._time()

    def _time(self) -> float:
        if self._now is not None:
            return float(self._now())
        import time

        return time.time()

    @property
    def total(self) -> int:
        return self._total

    def add(self, n: int = 1) -> int:
        if n <= 0:
            return self._total
        self._total += int(n)
        self._dirty = True
        return self._total

    def maybe_flush(self) -> bool:
        if not self._dirty:
            return False
        now = self._time()
        if (now - self._last_save) < self.min_save_interval_s:
            return False
        self.flush()
        return True

    def flush(self) -> None:
        _atomic_write(self.path, {"keys_typed": int(self._total)})
        self._dirty = False
        self._last_save = self._time()
