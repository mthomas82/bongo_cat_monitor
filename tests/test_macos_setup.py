#!/usr/bin/env python3
import os
import subprocess
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP = os.path.join(ROOT, "mac", "setup_macos.sh")


def sh(snippet: str) -> str:
    script = f"BONGO_SETUP_LIB=1 source {SETUP!r}; {snippet}"
    proc = subprocess.run(
        ["bash", "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


class MacSetupHelperTests(unittest.TestCase):
    def test_repo_root_is_project(self):
        out = sh("bongo_repo_root")
        self.assertEqual(os.path.realpath(out), os.path.realpath(ROOT))

    def test_find_python(self):
        out = sh("bongo_find_python")
        self.assertTrue(out)
        self.assertIn("python3", os.path.basename(out) + out)

    def test_python_ok_accepts_this_interpreter(self):
        py = sh("bongo_find_python")
        subprocess.run(
            ["bash", "-c", f"BONGO_SETUP_LIB=1 source {SETUP!r}; bongo_python_ok {py!r}"],
            cwd=ROOT,
            check=True,
        )

    def test_choose_without_gui_returns_default(self):
        out = sh('bongo_choose "hello" "Skip for now" "Try again" "Driver help" "Skip for now"')
        self.assertEqual(out, "Skip for now")

    def test_start_command_points_at_setup(self):
        cmd = os.path.join(ROOT, "Start Bongo Cat.command")
        with open(cmd, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("mac/setup_macos.sh", text)


if __name__ == "__main__":
    unittest.main()
