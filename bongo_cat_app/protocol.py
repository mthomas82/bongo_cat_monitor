"""Serial protocol helpers shared by the host and the CYD testbench.

Commands match bongo_cat.ino: newline-terminated ASCII at 115200 baud.
SPEED is a paw-frame delay in milliseconds (lower = faster typing).
"""

from __future__ import annotations

from typing import List, Optional

MAX_WPM = 200
MIN_SPEED_MS = 30
MAX_SPEED_MS = 500
STREAK_WPM = 65
CHARS_PER_WORD = 5.0
EXCITEMENT_IDLE_S = 600
SCREENSAVER_IDLE_S = 1200


def wpm_to_speed_ms(wpm: float) -> int:
    if wpm <= 0:
        return MAX_SPEED_MS
    clamped = min(float(wpm), MAX_WPM)
    normalized = clamped / MAX_WPM
    speed = MAX_SPEED_MS - (normalized * (MAX_SPEED_MS - MIN_SPEED_MS))
    return int(max(min(speed, MAX_SPEED_MS), MIN_SPEED_MS))


def streak_commands(wpm: float) -> List[str]:
    if wpm >= STREAK_WPM:
        return ["STREAK_ON"]
    return ["STREAK_OFF"]


def stats_command(cpu: int, ram: int, wpm: float) -> str:
    return f"STATS:CPU:{int(cpu)},RAM:{int(ram)},WPM:{int(round(wpm))}"


def typing_commands(wpm: float, cpu: int = 0, ram: int = 0) -> List[str]:
    """One burst of commands the host would send for this WPM."""
    cmds: List[str] = [stats_command(cpu, ram, wpm)]
    if wpm <= 0:
        cmds.append("STOP")
        cmds.append("STREAK_OFF")
        return cmds
    cmds.append(f"SPEED:{wpm_to_speed_ms(wpm)}")
    cmds.extend(streak_commands(wpm))
    return cmds


def mode_command(mode: str) -> str:
    if str(mode).strip().lower() == "mimic":
        return "MODE:MIMIC"
    return "MODE:GROOVE"


def tap_command(paw: str) -> str:
    side = str(paw).strip().upper()
    if side not in ("L", "R"):
        side = "L"
    return f"TAP:{side}"


def reaction_command(kind: str) -> str:
    name = str(kind).strip().upper()
    if name not in ("TYPO", "SAVE", "GROOM"):
        raise ValueError(f"unknown reaction: {kind}")
    return f"REACT:{name}"


def idle_milestone_command(
    idle_s: float, excitement_sent: bool, screensaver_sent: bool
) -> Optional[str]:
    """Host command for long keyboard absence. Screensaver wins if both are due."""
    if idle_s >= SCREENSAVER_IDLE_S and not screensaver_sent:
        return "SCREENSAVER"
    if idle_s >= EXCITEMENT_IDLE_S and not excitement_sent:
        return "EXCITED"
    return None


def keystroke_interval_seconds(wpm: float) -> Optional[float]:
    """Delay between spoofed keystrokes for a target WPM (5 chars = 1 word)."""
    if wpm <= 0:
        return None
    keys_per_second = (float(wpm) * CHARS_PER_WORD) / 60.0
    if keys_per_second <= 0:
        return None
    return 1.0 / keys_per_second
