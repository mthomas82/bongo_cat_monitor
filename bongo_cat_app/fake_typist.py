"""Spoof typing toward a Bongo Cat board (or a recording sink).

Does not inject OS-level key events. It sends the same serial commands
the real host would send, so you can watch the CYD without typing.
"""

from __future__ import annotations

import time
from typing import Callable, List, Protocol as TypingProtocol

from protocol import typing_commands, wpm_to_speed_ms

KEEPALIVE_S = 1.0

# (name, duration_seconds, wpm)
DEMO_PHASES = (
    ("idle", 2.0, 0),
    ("slow", 4.0, 15),
    ("normal", 4.0, 35),
    ("fast", 4.0, 55),
    ("streak", 5.0, 80),
    ("idle", 3.0, 0),
)


class CommandSink(TypingProtocol):
    def send(self, command: str) -> None: ...


class ListSink:
    def __init__(self) -> None:
        self.commands: List[str] = []

    def send(self, command: str) -> None:
        self.commands.append(command)


def virtual_clock():
    """Advance time only when sleep() is called. Safe for --dry-run."""
    t = [0.0]

    def now() -> float:
        return t[0]

    def sleep(dt: float) -> None:
        t[0] += max(dt, 0)

    return now, sleep


def play_session(
    sink: CommandSink,
    wpm: float,
    duration_s: float,
    cpu: int = 12,
    ram: int = 34,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Hold a typing (or idle) state for duration_s, then STOP."""
    for cmd in typing_commands(wpm, cpu=cpu, ram=ram):
        sink.send(cmd)

    start = now()
    while True:
        elapsed = now() - start
        remaining = duration_s - elapsed
        if remaining <= 0:
            break
        sleep(min(KEEPALIVE_S, remaining))
        if wpm > 0:
            sink.send(f"SPEED:{wpm_to_speed_ms(wpm)}")
            sink.send(typing_commands(wpm, cpu=cpu, ram=ram)[0])  # STATS

    if wpm > 0:
        sink.send("STREAK_OFF")
        sink.send("STOP")
