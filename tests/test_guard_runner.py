"""
Tests for askr/hooks/guard_runner.py.

NOTE: guard_runner.py is currently DEAD CODE -- nothing in the codebase
spawns it as the detached background subprocess its own docstring describes
(confirmed independently by two other sessions tonight; tracked in
askr_state/goals.jsonl under goal 36b2645f, plus a newer goal logged tonight
specifically about guard_runner.py never being invoked). It is still tested
here as a unit: untested dead code that later gets wired back up is a worse
state than dead code with real coverage behind it.

Isolation: get_state_dir() is exercised by chdir'ing into a tmp project dir
with its own askr_state/ (matches tests/test_multi_developer_e2e.py), and
the module's _NOTIFICATION_PATH constant is monkeypatched away from the real
~/.config/askr/notification.json (same pattern as
tests/test_task_approval_gate.py's session_start._NOTIFICATION_PATH swap).
check_and_save and Discord's send_message are always mocked -- no network,
no real guard_trigger/result files touched.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import guard_runner


class GuardRunnerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self.state_dir = os.path.join(self.project_dir, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)

        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

        self._orig_notification_path = guard_runner._NOTIFICATION_PATH
        guard_runner._NOTIFICATION_PATH = os.path.join(self.project_dir, "_notification.json")

    def tearDown(self):
        os.chdir(self._orig_cwd)
        guard_runner._NOTIFICATION_PATH = self._orig_notification_path
        self._tmp.cleanup()

    def _guard_log_path(self):
        return os.path.join(self.state_dir, "guard_log.md")

    def _dirty_result(self, **overrides):
        result = {
            "clean": False,
            "issues": ["writes directly to the DB layer, bypassing the repository interface"],
            "summary": "Bypasses the repository interface documented in architecture.md.",
            "trigger": {
                "reason": "shared_interface",
                "file_path": os.path.join(self.project_dir, "db.py"),
            },
            "timestamp": "2026-07-02T00:00:00+00:00",
        }
        result.update(overrides)
        return result

    # -- clean / no-trigger paths write nothing ---------------------------

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_clean_result_writes_nothing(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = {"clean": True}
        guard_runner.main()
        self.assertFalse(os.path.exists(guard_runner._NOTIFICATION_PATH))
        mock_discord.assert_not_called()
        self.assertFalse(os.path.exists(self._guard_log_path()))

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_no_pending_trigger_writes_nothing(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = None
        guard_runner.main()
        self.assertFalse(os.path.exists(guard_runner._NOTIFICATION_PATH))
        mock_discord.assert_not_called()

    def test_missing_state_dir_returns_early(self):
        nonexistent = os.path.join(self.project_dir, "does_not_exist", "askr_state")
        with patch("askr.state.config.get_state_dir", return_value=nonexistent), \
             patch("askr.session.guard.check_and_save") as mock_check:
            guard_runner.main()
            mock_check.assert_not_called()

    # -- non-clean result: notification.json --------------------------------

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_dirty_result_writes_notification_json(self, mock_check, mock_discord, mock_dev):
        result = self._dirty_result()
        mock_check.return_value = result
        guard_runner.main()

        with open(guard_runner._NOTIFICATION_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload["type"], "guard_warning")
        self.assertEqual(payload["summary"], result["summary"])
        self.assertEqual(payload["issues"], result["issues"])
        self.assertIn("db.py", payload["file_path"])
        self.assertFalse(payload["shown"])
        self.assertEqual(payload["timestamp"], result["timestamp"])

    # -- non-clean result: guard_log.md append format -----------------------

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_dirty_result_appends_guard_log(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = self._dirty_result()
        guard_runner.main()

        with open(self._guard_log_path()) as f:
            content = f.read()
        self.assertIn("# Guard Log", content)
        self.assertIn("Shared interface edit", content)
        self.assertIn("db.py", content)
        self.assertIn("Bypasses the repository interface", content)
        self.assertIn("Claude proceeded (non-blocking)", content)

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_guard_log_appends_without_duplicating_header(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = self._dirty_result()
        guard_runner.main()
        mock_check.return_value = self._dirty_result(summary="Second concern.")
        guard_runner.main()

        with open(self._guard_log_path()) as f:
            content = f.read()
        self.assertEqual(content.count("# Guard Log"), 1)
        self.assertIn("Second concern.", content)

    # -- Discord send attempt (mocked, no network) --------------------------

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message")
    @patch("askr.session.guard.check_and_save")
    def test_dirty_result_attempts_discord_send(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = self._dirty_result()
        mock_discord.return_value = (True, "")
        guard_runner.main()

        mock_discord.assert_called_once()
        (msg,), _ = mock_discord.call_args
        self.assertIn("db.py", msg)
        self.assertIn("Bypasses the repository interface", msg)

    @patch("askr.state.config.load_developer", return_value="dev")
    @patch("askr.clients.discord.send_message", side_effect=RuntimeError("network down"))
    @patch("askr.session.guard.check_and_save")
    def test_discord_failure_does_not_raise_and_log_still_written(self, mock_check, mock_discord, mock_dev):
        mock_check.return_value = self._dirty_result()
        guard_runner.main()  # must not raise despite send_message raising
        self.assertTrue(os.path.exists(self._guard_log_path()))


if __name__ == "__main__":
    unittest.main()
