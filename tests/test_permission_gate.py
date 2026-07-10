"""
Tests for askr/session/permission_gate.py — the Phase 5 approval-gate
detection logic (roadmap.md). Verifies each of the three independent
danger signals fires on its own, and that a clean project reports safe.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.permission_gate import is_dangerous_session


class PermissionGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_path = self._tmp.name
        os.makedirs(os.path.join(self.project_path, ".claude"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_settings(self, allowed_tools=None):
        path = os.path.join(self.project_path, ".claude", "settings.json")
        with open(path, "w") as f:
            json.dump({"allowedTools": allowed_tools or []}, f)

    def _write_settings_local(self, permissions_allow=None):
        path = os.path.join(self.project_path, ".claude", "settings.local.json")
        with open(path, "w") as f:
            json.dump({"permissions": {"allow": permissions_allow or []}}, f)

    def test_safe_project_no_settings_files(self):
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertFalse(dangerous)
        self.assertEqual(reasons, [])

    def test_safe_project_scoped_tools(self):
        self._write_settings(allowed_tools=["Read", "Edit", "Bash(git status)"])
        self._write_settings_local(permissions_allow=["Bash(git push)"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertFalse(dangerous)

    def test_unrestricted_bash_in_allowed_tools(self):
        self._write_settings(allowed_tools=["Read", "Bash(*)"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertTrue(dangerous)
        self.assertTrue(any("allowedTools" in r for r in reasons))

    def test_bare_bash_in_allowed_tools(self):
        self._write_settings(allowed_tools=["Bash"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertTrue(dangerous)

    def test_rm_pattern_in_permissions_allow(self):
        self._write_settings_local(permissions_allow=["Bash(rm -rf /tmp/foo)"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertTrue(dangerous)
        self.assertTrue(any("permissions.allow" in r for r in reasons))

    def test_multiple_reasons_all_reported(self):
        self._write_settings(allowed_tools=["Bash(*)"])
        self._write_settings_local(permissions_allow=["Bash(rm -rf *)"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertTrue(dangerous)
        self.assertEqual(len(reasons), 2)

    def test_malformed_settings_json_fails_safe(self):
        path = os.path.join(self.project_path, ".claude", "settings.json")
        with open(path, "w") as f:
            f.write("{not valid json")
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertFalse(dangerous)


class SkipPermissionsOnlyModeTests(unittest.TestCase):
    """
    2026-07-11: skip_permissions_only=True is used by the autonomous-relaunch
    gate (lifecycle._launch_gate_check) — unlike the cross-dev queue gate,
    broad allowedTools (Phase 3.8's normal state) must NOT count here.
    """
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_path = self._tmp.name
        os.makedirs(os.path.join(self.project_path, ".claude"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_settings(self, allowed_tools=None):
        path = os.path.join(self.project_path, ".claude", "settings.json")
        with open(path, "w") as f:
            json.dump({"allowedTools": allowed_tools or []}, f)

    def _write_settings_local(self, permissions_allow=None):
        path = os.path.join(self.project_path, ".claude", "settings.local.json")
        with open(path, "w") as f:
            json.dump({"permissions": {"allow": permissions_allow or []}}, f)

    def test_unrestricted_bash_alone_is_not_dangerous(self):
        self._write_settings(allowed_tools=["Read", "Bash(*)", "Bash"])
        dangerous, reasons = is_dangerous_session(self.project_path, skip_permissions_only=True)
        self.assertFalse(dangerous)
        self.assertEqual(reasons, [])

    def test_rm_pattern_alone_is_not_dangerous(self):
        self._write_settings_local(permissions_allow=["Bash(rm -rf /tmp/foo)"])
        dangerous, reasons = is_dangerous_session(self.project_path, skip_permissions_only=True)
        self.assertFalse(dangerous)

    def test_skip_permissions_flag_still_counts(self):
        from unittest.mock import patch
        with patch("askr.session.permission_gate._claude_launch_args_dangerous", return_value=True):
            dangerous, reasons = is_dangerous_session(self.project_path, skip_permissions_only=True)
        self.assertTrue(dangerous)
        self.assertEqual(reasons, ["--dangerously-skip-permissions in session launch args"])

    def test_default_mode_unchanged_still_checks_all_three(self):
        self._write_settings(allowed_tools=["Bash(*)"])
        dangerous, reasons = is_dangerous_session(self.project_path)
        self.assertTrue(dangerous)


if __name__ == "__main__":
    unittest.main()
