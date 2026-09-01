#!/usr/bin/env python3
import os
import socket
import sys
import time
import unittest
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bongo_cat_app"))

from sprite_studio_ctl import SpriteStudioController  # noqa: E402


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _http_ok(url: str, timeout: float = 0.4) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


class SpriteStudioControllerTests(unittest.TestCase):
    def setUp(self):
        self.port = _free_port()
        self.ctl = SpriteStudioController(
            repo_root=ROOT,
            port=self.port,
            command=[
                sys.executable,
                "-m",
                "http.server",
                str(self.port),
                "--bind",
                "127.0.0.1",
            ],
        )

    def tearDown(self):
        self.ctl.stop()

    def test_not_running_on_fresh_port(self):
        self.assertFalse(self.ctl.is_running())

    def test_start_then_http_then_stop(self):
        result = self.ctl.start()
        self.assertTrue(result["ok"], result)
        deadline = time.time() + 5
        while time.time() < deadline and not self.ctl.is_running():
            time.sleep(0.05)
        self.assertTrue(self.ctl.is_running())
        self.assertTrue(_http_ok(f"http://127.0.0.1:{self.port}/"))
        stop = self.ctl.stop()
        self.assertTrue(stop["ok"], stop)
        deadline = time.time() + 5
        while time.time() < deadline and self.ctl.is_running():
            time.sleep(0.05)
        self.assertFalse(self.ctl.is_running())

    def test_start_when_already_running_is_ok(self):
        self.assertTrue(self.ctl.start()["ok"])
        deadline = time.time() + 5
        while time.time() < deadline and not self.ctl.is_running():
            time.sleep(0.05)
        again = self.ctl.start()
        self.assertTrue(again["ok"], again)
        self.assertTrue(again.get("already"))

    def test_stop_when_not_running_is_ok(self):
        result = self.ctl.stop()
        self.assertTrue(result["ok"], result)


class RealSpriteStudioTests(unittest.TestCase):
    def test_default_command_serves_catalog(self):
        port = _free_port()
        ctl = SpriteStudioController(repo_root=ROOT, port=port)
        result = ctl.start()
        self.addCleanup(ctl.stop)
        self.assertTrue(result["ok"], result)
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/catalog", timeout=3) as r:
            body = r.read().decode()
        self.assertIn("sprites", body)
        self.assertIn("palette", body)
        self.assertTrue(ctl.stop()["ok"])
        self.assertFalse(ctl.is_running())


if __name__ == "__main__":
    unittest.main()
