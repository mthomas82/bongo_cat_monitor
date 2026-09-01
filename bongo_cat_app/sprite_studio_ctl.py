#!/usr/bin/env python3
"""Start and stop the Bongo Cat sprite studio HTTP server from the host app."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


DEFAULT_PORT = 8765


def repo_root_from_app() -> Path:
    here = Path(__file__).resolve().parent
    if here.name == "bongo_cat_app":
        return here.parent
    return here


class SpriteStudioController:
    def __init__(
        self,
        repo_root: str | Path | None = None,
        port: int = DEFAULT_PORT,
        command: list[str] | None = None,
        python: str | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else repo_root_from_app()
        self.port = int(port)
        self.command = command
        self.python = python or sys.executable
        self._proc: subprocess.Popen | None = None

    def default_command(self) -> list[str]:
        script = self.repo_root / "tools" / "sprite_studio.py"
        return [
            self.python,
            str(script),
            "--no-browser",
            "--port",
            str(self.port),
        ]

    def is_running(self) -> bool:
        return self._port_open()

    def start(self) -> dict:
        if self.is_running():
            return {"ok": True, "already": True, "port": self.port}
        cmd = list(self.command or self.default_command())
        try:
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(self.repo_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return {"ok": False, "error": str(exc), "port": self.port}
        deadline = time.time() + 5
        while time.time() < deadline and not self._port_open():
            if self._proc.poll() is not None:
                self._proc = None
                return {"ok": False, "error": "sprite studio exited before opening the port", "port": self.port}
            time.sleep(0.05)
        if not self._port_open():
            return {"ok": False, "error": f"port {self.port} did not open", "port": self.port, "pid": self._proc.pid}
        return {"ok": True, "pid": self._proc.pid, "port": self.port}

    def stop(self) -> dict:
        if not self.is_running() and (self._proc is None or self._proc.poll() is not None):
            self._proc = None
            return {"ok": True, "already": True, "port": self.port}

        pids = set(self._pids_on_port())
        if self._proc is not None and self._proc.poll() is None:
            pids.add(self._proc.pid)
            try:
                pids.add(os.getpgid(self._proc.pid))
            except OSError:
                pass

        for pid in list(pids):
            self._terminate(pid)

        deadline = time.time() + 4
        while time.time() < deadline and self._port_open():
            time.sleep(0.05)

        if self._port_open():
            for pid in self._pids_on_port():
                self._kill(pid)
            deadline = time.time() + 2
            while time.time() < deadline and self._port_open():
                time.sleep(0.05)

        if self._proc is not None:
            try:
                self._proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            self._proc = None

        if self._port_open():
            return {"ok": False, "error": f"port {self.port} still in use", "port": self.port}
        return {"ok": True, "port": self.port}

    def local_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def _port_open(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.port), timeout=0.2):
                return True
        except OSError:
            return False

    def _pids_on_port(self) -> list[int]:
        try:
            out = subprocess.check_output(
                ["lsof", "-t", f"-iTCP:{self.port}", "-sTCP:LISTEN"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError):
            return []
        pids = []
        for line in out.split():
            try:
                pids.append(int(line))
            except ValueError:
                continue
        return pids

    def _terminate(self, pid: int) -> None:
        try:
            os.killpg(pid, signal.SIGTERM)
            return
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    def _kill(self, pid: int) -> None:
        try:
            os.killpg(pid, signal.SIGKILL)
            return
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass
