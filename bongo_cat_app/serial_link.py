#!/usr/bin/env python3
"""Serial drop detection and reconnect scheduling (no hardware)."""

import errno

SERIAL_RECONNECT_INTERVAL = 3.0

_DROP_ERRNOS = {
    errno.EIO,
    errno.ENXIO,
    errno.ENODEV,
    getattr(errno, "ENOENT", 2),
}

_DROP_NEEDLES = (
    "input/output error",
    "errno 5",
    "device disconnected",
    "device not configured",
    "no such file or directory",
)


def is_serial_drop_error(exc) -> bool:
    if exc is None:
        return False
    if isinstance(exc, TimeoutError):
        return False
    en = getattr(exc, "errno", None)
    if en == errno.EACCES:
        return False
    if en in _DROP_ERRNOS:
        return True
    msg = str(exc).lower()
    return any(n in msg for n in _DROP_NEEDLES)


def port_after_drop(current_port, existing_devices) -> str:
    if not current_port or current_port == "AUTO":
        return "AUTO"
    if current_port in existing_devices:
        return current_port
    return "AUTO"


def should_attempt_reconnect(
    serial_is_open,
    now,
    last_attempt,
    interval=SERIAL_RECONNECT_INTERVAL,
) -> bool:
    if serial_is_open:
        return False
    if last_attempt is None:
        return True
    return (now - last_attempt) >= interval
