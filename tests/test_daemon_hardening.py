"""
Tests for two daemon-reliability fixes found 2026-07-16:

1. A launchd job was silently registered pointing at a temp-directory
   StandardOutPath (almost certainly a manual HOME-overridden invocation),
   and because KeepAlive respawns reuse launchd's cached job definition
   rather than re-reading the plist, the daemon polled correctly but logged
   into a dead temp file for days with zero visible symptom.
   _install_launchd() now refuses to register when HOME resolves inside the
   OS temp directory.

2. Even with a correctly-registered daemon, there was no way to detect this
   class of failure from the outside — the daemon looked "running" (real
   PID, real PID file) while doing nothing observable. _daemon_liveness_warning()
   is a dead-man's-switch: called only when a session is genuinely active,
   it flags daemon.log staleness as a probable stuck daemon.
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli import askr


class HomeIsTempSandboxTests(unittest.TestCase):
    def test_real_home_is_not_a_sandbox(self):
        with patch("os.path.expanduser", side_effect=lambda p: p.replace("~", "/Users/realuser")):
            self.assertFalse(askr._home_is_temp_sandbox())

    def test_home_inside_tempdir_is_a_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake_home = os.path.join(tmp, "sandbox_home")
            os.makedirs(fake_home)
            with patch("os.path.expanduser", side_effect=lambda p: p.replace("~", fake_home)), \
                 patch("tempfile.gettempdir", return_value=tmp):
                self.assertTrue(askr._home_is_temp_sandbox())

    def test_home_equal_to_tempdir_itself_is_a_sandbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("os.path.expanduser", side_effect=lambda p: p.replace("~", tmp)), \
                 patch("tempfile.gettempdir", return_value=tmp):
                self.assertTrue(askr._home_is_temp_sandbox())


class InstallLaunchdRefusesSandboxTests(unittest.TestCase):
    def test_install_launchd_refuses_when_home_is_sandbox(self):
        with patch.object(askr, "_home_is_temp_sandbox", return_value=True), \
             patch("subprocess.run") as mock_run:
            ok, detail = askr._install_launchd()
        self.assertFalse(ok)
        self.assertIn("temp", detail.lower())
        mock_run.assert_not_called()  # never even gets to launchctl


class DaemonLivenessWarningTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._log_path = os.path.join(self._tmp.name, "daemon.log")
        self._patch = patch.object(askr, "_DAEMON_LOG_PATH", self._log_path)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_fresh_log_is_healthy(self):
        with open(self._log_path, "w") as f:
            f.write("[...] ok: ctx=10% quota=5%\n")
        self.assertIsNone(askr._daemon_liveness_warning())

    def test_stale_log_warns(self):
        with open(self._log_path, "w") as f:
            f.write("[...] daemon started\n")
        old = time.time() - 300  # 5 minutes ago, past the 120s threshold
        os.utime(self._log_path, (old, old))
        warning = askr._daemon_liveness_warning()
        self.assertIsNotNone(warning)
        self.assertIn("stuck", warning.lower())

    def test_missing_log_warns_differently(self):
        warning = askr._daemon_liveness_warning()
        self.assertIsNotNone(warning)
        self.assertIn("not found", warning.lower())


if __name__ == "__main__":
    unittest.main()
