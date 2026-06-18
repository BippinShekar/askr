"""
Tests for `askr init` idempotency: a second call with an unchanged plist and a
healthy daemon must not touch launchd at all (no unload/load cycle), since that
wipes the daemon's in-memory trigger/dedup state for no reason.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli.askr import _install_launchd


class InstallLaunchdIdempotencyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.plist_path = os.path.join(self._tmp.name, "com.askr.daemon.plist")
        self.log_path = os.path.join(self._tmp.name, "daemon.log")

        real_expanduser = os.path.expanduser

        def fake_expanduser(path):
            if path == "~/Library/LaunchAgents/com.askr.daemon.plist":
                return self.plist_path
            if path == "~/.config/askr/daemon.log":
                return self.log_path
            return real_expanduser(path)

        self.expanduser_patch = patch("os.path.expanduser", side_effect=fake_expanduser)
        self.expanduser_patch.start()

        def fake_run(args, **kwargs):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "/usr/bin:/bin"
            return result

        self.run_patch = patch("subprocess.run", side_effect=fake_run)
        self.mock_run = self.run_patch.start()

    def tearDown(self):
        self.expanduser_patch.stop()
        self.run_patch.stop()
        self._tmp.cleanup()

    def _launchctl_calls(self):
        return [c for c in self.mock_run.call_args_list if c.args[0][0] == "launchctl"]

    def test_first_install_loads_via_launchctl(self):
        with patch("askr.session.lifecycle.daemon_is_running", return_value=True):
            ok, path = _install_launchd()

        self.assertTrue(ok)
        self.assertEqual(path, self.plist_path)
        self.assertTrue(os.path.exists(self.plist_path))
        launchctl_calls = self._launchctl_calls()
        self.assertEqual(len(launchctl_calls), 2)  # unload + load
        self.assertEqual(launchctl_calls[1].args[0], ["launchctl", "load", self.plist_path])

    def test_second_install_skips_launchctl_when_healthy_and_unchanged(self):
        with patch("askr.session.lifecycle.daemon_is_running", return_value=True):
            _install_launchd()
            self.mock_run.reset_mock()

            ok, path = _install_launchd()

        self.assertTrue(ok)
        self.assertEqual(path, self.plist_path)
        self.assertEqual(self._launchctl_calls(), [])

    def test_second_install_reloads_when_daemon_unhealthy(self):
        with patch("askr.session.lifecycle.daemon_is_running", return_value=True):
            _install_launchd()

        with patch("askr.session.lifecycle.daemon_is_running", return_value=False):
            self.mock_run.reset_mock()
            ok, path = _install_launchd()

        self.assertTrue(ok)
        self.assertEqual(len(self._launchctl_calls()), 2)

    def test_second_install_reloads_when_plist_changed(self):
        with patch("askr.session.lifecycle.daemon_is_running", return_value=True):
            _install_launchd()

            with open(self.plist_path, "w") as f:
                f.write("<changed/>")

            self.mock_run.reset_mock()
            ok, path = _install_launchd()

        self.assertTrue(ok)
        self.assertEqual(len(self._launchctl_calls()), 2)


if __name__ == "__main__":
    unittest.main()
