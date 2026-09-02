"""Per-key mimic taps and host-side reaction detectors.

Groove mode never emits TAP; Mimic mode does. Reactions work in both.
"""

from __future__ import annotations

from typing import List, Optional, Set

from protocol import mode_command

TYPO_COUNT = 4
TYPO_WINDOW_S = 1.5
TYPO_COOLDOWN_S = 2.0
SAVE_COOLDOWN_S = 1.0
GROOM_AFTER_S = 2.5
GROOM_UNTIL_S = 8.0


def _key_text(key) -> str:
    return str(key).lower()


def _is_modifier(key) -> bool:
    s = _key_text(key)
    return any(token in s for token in ("ctrl", "cmd", "alt", "shift"))


def _is_erase(key) -> bool:
    s = _key_text(key)
    return "backspace" in s or s.endswith(".delete") or s == "key.delete"


def _is_s_key(key) -> bool:
    s = _key_text(key).strip()
    return s in ("'s'", "s", "key.s") or s.endswith("'s'")


def _is_ctrl(key) -> bool:
    return "ctrl" in _key_text(key)


def _is_cmd(key) -> bool:
    s = _key_text(key)
    return "cmd" in s or "cmd_l" in s or "cmd_r" in s


class MimicController:
    def __init__(self, mode: str = "groove") -> None:
        self.mode = "mimic" if str(mode).lower() == "mimic" else "groove"
        self._held: Set[str] = set()
        self._next_paw = "L"
        self._ctrl = False
        self._cmd = False
        self._backspaces: List[float] = []
        self._last_typo = -1e9
        self._last_save = -1e9
        self._idle_since: Optional[float] = None
        self._groom_sent = False

    def set_mode(self, mode: str) -> List[str]:
        self.mode = "mimic" if str(mode).lower() == "mimic" else "groove"
        return [mode_command(self.mode)]

    def on_press(self, key, now: float) -> List[str]:
        kid = str(key)
        cmds: List[str] = []
        is_repeat = kid in self._held
        if not is_repeat:
            self._held.add(kid)

        if _is_ctrl(key):
            self._ctrl = True
        if _is_cmd(key):
            self._cmd = True

        if not is_repeat and (self._ctrl or self._cmd) and _is_s_key(key):
            if now - self._last_save >= SAVE_COOLDOWN_S:
                self._last_save = now
                cmds.append("REACT:SAVE")

        if not is_repeat and _is_erase(key):
            self._backspaces.append(now)
            cutoff = now - TYPO_WINDOW_S
            self._backspaces = [t for t in self._backspaces if t >= cutoff]
            if (
                len(self._backspaces) >= TYPO_COUNT
                and now - self._last_typo >= TYPO_COOLDOWN_S
            ):
                self._last_typo = now
                cmds.append("REACT:TYPO")

        if not is_repeat and not _is_modifier(key):
            self._idle_since = None
            self._groom_sent = False

        if (
            self.mode == "mimic"
            and not is_repeat
            and not _is_modifier(key)
        ):
            paw = self._next_paw
            self._next_paw = "R" if paw == "L" else "L"
            cmds.append(f"TAP:{paw}")

        return cmds

    def on_release(self, key, now: float) -> List[str]:
        kid = str(key)
        self._held.discard(kid)
        if _is_ctrl(key):
            self._ctrl = any(_is_ctrl(k) for k in self._held)
        if _is_cmd(key):
            self._cmd = any(_is_cmd(k) for k in self._held)
        return []

    def on_typing_idle(self, now: float) -> None:
        if self._idle_since is None:
            self._idle_since = now
            self._groom_sent = False

    def on_typing_active(self) -> None:
        self._idle_since = None
        self._groom_sent = False

    def poll(self, now: float) -> List[str]:
        if self._idle_since is None or self._groom_sent:
            return []
        elapsed = now - self._idle_since
        if GROOM_AFTER_S <= elapsed < GROOM_UNTIL_S:
            self._groom_sent = True
            return ["REACT:GROOM"]
        if elapsed >= GROOM_UNTIL_S:
            self._groom_sent = True
        return []
