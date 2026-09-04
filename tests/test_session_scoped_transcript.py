"""
Regression tests for the 2026-09-04 same-session-resume bug: multiple
concurrent Claude Code sessions in one project directory (Cursor's Agents
grid running several background agents against the same repo) each get
their own quota trigger with a real session_id, but several call sites threw
that session_id away before resolving the active transcript —
_find_active_jsonl(project_path) without session_id falls back to "newest
mtime in the project," which silently picks a DIFFERENT session's transcript
whenever 2+ sessions are live. Live-reproduced: askr sent Escape/'cont' to an
unrelated session while the one that actually hit its quota limit sat
untouched.

Each test below asserts the fixed call sites pass session_id through to
_find_active_jsonl instead of relying on the ambiguous mtime fallback.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class QuotaTriggerImplTests(unittest.TestCase):
    def test_passes_session_id_to_find_active_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
                 patch("askr.state.config.load_developer", return_value="dev"), \
                 patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
                 patch.object(lifecycle, "_wait_for_turn_to_finish"), \
                 patch("askr.session.monitor._find_active_jsonl", return_value="") as mock_find, \
                 patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
                 patch.object(lifecycle, "_get_next_goal", return_value=""), \
                 patch.object(lifecycle, "_write_launch_mode"), \
                 patch.object(lifecycle, "_write_notification"), \
                 patch.object(lifecycle, "_find_session_pid", return_value=None), \
                 patch.object(lifecycle, "_wait_for_reset"), \
                 patch.object(lifecycle.time, "sleep"), \
                 patch.object(lifecycle, "_start_claude", return_value=False), \
                 patch.object(lifecycle, "_notify_discord_resumed"), \
                 patch.object(lifecycle, "_write_resumed_marker"), \
                 patch("askr.state.analytics.today_summary", return_value={"total_seconds": 0}):
                lifecycle._execute_quota_trigger_impl(
                    {"quota_pct": 95.0}, tmp, session_id="session-B",
                )
        mock_find.assert_called_once_with(tmp, "session-B")


class IdleCheckpointTests(unittest.TestCase):
    def test_passes_session_id_to_find_active_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            with patch("askr.state.config.load_developer", return_value="dev"), \
                 patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
                 patch("askr.session.monitor._find_active_jsonl", return_value="") as mock_find, \
                 patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
                 patch.object(lifecycle, "_speak"):
                lifecycle._execute_idle_checkpoint(
                    {}, tmp, session_id="session-B",
                )
        mock_find.assert_called_once_with(tmp, "session-B")

    def test_thread_passes_session_id_through_from_trigger_evaluation(self):
        """The Trigger C thread target=args tuple must include session_id —
        this is the exact line that silently dropped it before the fix."""
        import inspect
        src = inspect.getsource(lifecycle._evaluate_session_triggers)
        self.assertIn("target=_execute_idle_checkpoint,\n            args=(stats, project_path, session_id)", src)


class TurnMarkerStillLiveTests(unittest.TestCase):
    def test_passes_session_id_to_find_active_jsonl(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]), \
             patch("askr.session.monitor._find_active_jsonl", return_value="") as mock_find:
            lifecycle._turn_marker_still_live("/fake/project", "session-B")
        mock_find.assert_called_once_with("/fake/project", "session-B")


class WaitForTurnToFinishTranscriptTests(unittest.TestCase):
    def test_outstanding_subagent_check_scoped_to_session_id(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop", return_value=(123.0, 3)), \
             patch("askr.session.checkpoint.has_outstanding_subagent", return_value=False), \
             patch("askr.session.monitor._find_active_jsonl", return_value="") as mock_find, \
             patch.object(lifecycle.time, "sleep"):
            lifecycle._wait_for_turn_to_finish("/fake/project", "session-B", require_quiet_grace=False)
        mock_find.assert_called_once_with("/fake/project", "session-B")


class OpenCompanionSessionTests(unittest.TestCase):
    def test_passes_session_id_to_find_active_jsonl_and_pre_kill(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            with patch.object(lifecycle, "_pre_kill_update_tools") as mock_pre_kill, \
                 patch("askr.state.config.load_developer", return_value="dev"), \
                 patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
                 patch("askr.session.monitor._find_active_jsonl", return_value="") as mock_find, \
                 patch.object(lifecycle, "_get_next_goal", return_value=""), \
                 patch.object(lifecycle, "_write_launch_mode"), \
                 patch.object(lifecycle, "_load_allowed_tools", return_value=[]), \
                 patch.object(lifecycle, "_infer_direction", return_value={"confidence": 0.0, "direction": ""}), \
                 patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[]), \
                 patch.object(lifecycle, "_NOTIFICATION_PATH", os.path.join(tmp, "notification.json")), \
                 patch.object(lifecycle, "_spawn_terminal_app_fallback"), \
                 patch.object(lifecycle, "_speak"), \
                 patch("askr.state.writer.append_event"):
                lifecycle._open_companion_session(tmp, session_id="session-B")
        mock_pre_kill.assert_called_once_with(tmp, "session-B")
        mock_find.assert_called_once_with(tmp, "session-B")


if __name__ == "__main__":
    unittest.main()
