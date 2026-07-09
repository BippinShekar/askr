"""
Tests for the launch-holding side of the dangerous-permissions gate:
lifecycle.py's _launch_gate_check/_consume_launch_approval_flag/
_notify_launch_held, and askr.py's `askr launch approve` command.

Extends the Phase 5 approval gate (which only held a teammate's queued task)
to cover askr's own autonomous relaunch — a companion/goal session started by
askr inherits the exact same permission-gate risk from whatever session
triggered it, so it needs the same hold-until-approved behavior.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class LaunchGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_path = self._tmp.name
        os.makedirs(os.path.join(self.project_path, "askr_state", "tasks"), exist_ok=True)
        os.makedirs(os.path.join(self.project_path, ".claude"), exist_ok=True)

        self._notif_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._orig_notif_path = lifecycle._NOTIFICATION_PATH
        lifecycle._NOTIFICATION_PATH = self._notif_tmp.name

    def tearDown(self):
        self._tmp.cleanup()
        lifecycle._NOTIFICATION_PATH = self._orig_notif_path
        try:
            os.remove(self._notif_tmp.name)
        except Exception:
            pass

    def _write_settings(self, allowed_tools=None):
        path = os.path.join(self.project_path, ".claude", "settings.json")
        with open(path, "w") as f:
            json.dump({"allowedTools": allowed_tools or []}, f)

    def test_approval_flag_is_one_shot(self):
        self.assertFalse(lifecycle._consume_launch_approval_flag(self.project_path, "dev"))
        flag_path = os.path.join(self.project_path, "askr_state", "tasks", "launch_approved_dev.flag")
        with open(flag_path, "w") as f:
            f.write("2026-07-09T00:00:00Z\n")
        self.assertTrue(lifecycle._consume_launch_approval_flag(self.project_path, "dev"))
        # consumed — a second check must not find it again
        self.assertFalse(lifecycle._consume_launch_approval_flag(self.project_path, "dev"))

    def test_notify_writes_dangerous_autolaunch_pending_payload(self):
        lifecycle._notify_launch_held(self.project_path, "dev", ["unrestricted Bash in .claude/settings.json allowedTools"])
        with open(lifecycle._NOTIFICATION_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload["type"], "dangerous_autolaunch_pending")
        self.assertEqual(payload["developer"], "dev")
        self.assertIn("dev", payload["message"])

    def test_gate_proceeds_when_session_is_safe(self):
        self._write_settings(allowed_tools=["Read", "Edit"])
        self.assertTrue(lifecycle._launch_gate_check(self.project_path, "dev"))
        # no hold notification should have been written
        with open(lifecycle._NOTIFICATION_PATH) as f:
            content = f.read()
        self.assertEqual(content, "")

    def test_gate_holds_when_session_is_dangerous_and_unapproved(self):
        self._write_settings(allowed_tools=["Bash(*)"])
        self.assertFalse(lifecycle._launch_gate_check(self.project_path, "dev"))
        with open(lifecycle._NOTIFICATION_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload["type"], "dangerous_autolaunch_pending")

    def test_gate_proceeds_when_dangerous_but_approved(self):
        self._write_settings(allowed_tools=["Bash(*)"])
        flag_path = os.path.join(self.project_path, "askr_state", "tasks", "launch_approved_dev.flag")
        with open(flag_path, "w") as f:
            f.write("2026-07-09T00:00:00Z\n")
        self.assertTrue(lifecycle._launch_gate_check(self.project_path, "dev"))

    def test_start_claude_held_when_dangerous(self):
        self._write_settings(allowed_tools=["Bash(*)"])
        with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
             patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[]), \
             patch("askr.state.config.load_developer", return_value="dev"):
            launched = lifecycle._start_claude(self.project_path, force=True)
        self.assertFalse(launched)
        with open(lifecycle._NOTIFICATION_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload["type"], "dangerous_autolaunch_pending")


if __name__ == "__main__":
    unittest.main()
