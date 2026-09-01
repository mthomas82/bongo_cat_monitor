"""ESP32 USB-serial port detection (Windows / macOS / Linux)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

# CP210x, CH340/CH341, FTDI, Espressif native USB
KNOWN_VIDS = {0x10C4, 0x1A86, 0x0403, 0x303A}

KEYWORDS = (
    "CP210",
    "CH340",
    "CH341",
    "FT232",
    "FTDI",
    "ESP32",
    "SILICON LABS",
    "QINHENG",
    "WCH",
    "USB SERIAL",
    "USB-SERIAL",
    "SLAB_USBTOUART",
)

PATH_PATTERNS = (
    "usbserial",
    "usbmodem",
    "wchusbserial",
    "slab_usb",
    "usb_serial",
    "ttyusb",
    "ttyacm",
)


@dataclass(frozen=True)
class PortInfo:
    device: str
    description: str = ""
    manufacturer: str = ""
    vid: Optional[int] = None
    hwid: str = ""

    @property
    def path_lower(self) -> str:
        return self.device.lower().replace("\\", "/")


def is_macos_tty_twin(device: str) -> bool:
    """On macOS, /dev/tty.* is the call-in twin of /dev/cu.*; prefer cu."""
    name = os.path.basename(device)
    return sys.platform == "darwin" and name.startswith("tty.")


def is_likely_esp32(port: PortInfo) -> bool:
    if port.vid is not None and port.vid in KNOWN_VIDS:
        return True
    blob = " ".join(
        [
            port.description or "",
            port.manufacturer or "",
            port.hwid or "",
            port.device or "",
        ]
    ).upper()
    if any(k in blob for k in KEYWORDS):
        return True
    path = port.path_lower
    return any(p in path for p in PATH_PATTERNS)


def rank_port(port: PortInfo) -> tuple:
    """Lower tuple sorts first. Prefer cu.* USB adapters over tty twins / debug consoles."""
    path = port.path_lower
    vid_hit = 0 if (port.vid in KNOWN_VIDS) else 1
    cu = 0 if "/cu." in path or path.startswith("cu.") else 1
    debug = 1 if "bluetooth" in path or "debug-console" in path else 0
    return (debug, vid_hit, cu, path)


def dedupe_macos_cu(ports: Sequence[PortInfo]) -> List[PortInfo]:
    """Drop /dev/tty.* when the matching /dev/cu.* is already a candidate."""
    cu_stems = set()
    for p in ports:
        base = os.path.basename(p.device)
        if base.startswith("cu."):
            cu_stems.add(base[3:])
    out: List[PortInfo] = []
    for p in ports:
        base = os.path.basename(p.device)
        if base.startswith("tty.") and base[4:] in cu_stems:
            continue
        out.append(p)
    return out


def select_port(ports: Iterable[PortInfo]) -> Optional[PortInfo]:
    candidates = [p for p in ports if is_likely_esp32(p) and not is_macos_tty_twin(p.device)]
    candidates = dedupe_macos_cu(candidates)
    if not candidates:
        return None
    return sorted(candidates, key=rank_port)[0]


def from_pyserial(port) -> PortInfo:
    vid = None
    try:
        if getattr(port, "vid", None) is not None:
            vid = int(port.vid)
    except (TypeError, ValueError):
        vid = None
    return PortInfo(
        device=port.device,
        description=str(getattr(port, "description", "") or ""),
        manufacturer=str(getattr(port, "manufacturer", "") or ""),
        vid=vid,
        hwid=str(getattr(port, "hwid", "") or ""),
    )


def list_system_ports() -> List[PortInfo]:
    import serial.tools.list_ports

    return [from_pyserial(p) for p in serial.tools.list_ports.comports()]


def find_esp32_device(explicit: Optional[str] = None) -> Optional[str]:
    if explicit and explicit.upper() not in ("", "AUTO"):
        return explicit
    chosen = select_port(list_system_ports())
    return chosen.device if chosen else None
