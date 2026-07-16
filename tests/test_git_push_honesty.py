"""
Regression tests for a real, documented bug: git_commit_push() had no return
value at all (every path — success, no-op, and failure — implicitly returned
None), so nothing downstream could tell a successful push from a failed one.
Every caller (voice announcements, Discord messages, the next-session
custom_instructions text) unconditionally claimed "state saved to git"
regardless of outcome. ~/.config/askr/checkpoint_error.log has a documented
history of real push failures (unresolved merge conflicts, network errors,
rebase conflicts on askr's own files, timeouts) that were silently mismatched
against a confident "state saved to git" announcement every single time.

git_commit_push() now returns (success: bool, error_detail: str), threaded
through create_checkpoint()'s result dict as result["git_pushed"] /
result["git_push_error"], and every caller must check it before claiming
success.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import checkpoint, lifecycle


def _mock_run(returncode=0, stdout="", stderr=""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class GitCommitPushReturnValueTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_nothing_to_commit_is_success(self):
        # git status --porcelain returns empty -> nothing changed -> True, no lie.
        with patch("subprocess.run", return_value=_mock_run(stdout="")):
            success, err = checkpoint.git_commit_push(self.state_dir, "dev", "idle")
        self.assertTrue(success)
        self.assertEqual(err, "")

    def test_successful_push_returns_true(self):
        calls = [
            _mock_run(stdout=""),                       # git add
            _mock_run(stdout="M askr_state/x.md\n"),     # git status --porcelain (dirty)
            _mock_run(),                                 # git commit
            _mock_run(returncode=0),                     # git pull --rebase
            _mock_run(returncode=0),                     # git push
        ]
        with patch("subprocess.run", side_effect=calls):
            success, err = checkpoint.git_commit_push(self.state_dir, "dev", "idle")
        self.assertTrue(success)
        self.assertEqual(err, "")

    def test_push_rejected_returns_false_with_detail(self):
        calls = [
            _mock_run(stdout=""),                        # git add
            _mock_run(stdout="M askr_state/x.md\n"),      # git status (dirty)
            _mock_run(),                                  # git commit
            _mock_run(returncode=0),                      # pull ok
            _mock_run(returncode=1, stderr="rejected"),    # push fails
            _mock_run(returncode=0),                       # pull retry
            _mock_run(returncode=1, stderr="rejected again"),  # push retry fails
        ]
        with patch("subprocess.run", side_effect=calls), \
             patch.object(checkpoint, "_log_push_failure") as mock_log:
            success, err = checkpoint.git_commit_push(self.state_dir, "dev", "idle")
        self.assertFalse(success)
        self.assertIn("rejected again", err)
        mock_log.assert_called_once()

    def test_rebase_conflict_aborts_and_returns_false(self):
        calls = [
            _mock_run(stdout=""),                                  # git add
            _mock_run(stdout="M askr_state/x.md\n"),                # git status (dirty)
            _mock_run(),                                            # git commit
            _mock_run(returncode=1, stderr="unresolved conflict"),  # pull --rebase fails
            _mock_run(),                                            # rebase --abort
        ]
        with patch("subprocess.run", side_effect=calls), \
             patch.object(checkpoint, "_log_push_failure"):
            success, err = checkpoint.git_commit_push(self.state_dir, "dev", "idle")
        self.assertFalse(success)
        self.assertIn("unresolved conflict", err)

    def test_exception_returns_false_not_raise(self):
        with patch("subprocess.run", side_effect=OSError("git not found")), \
             patch.object(checkpoint, "_log_push_failure"):
            success, err = checkpoint.git_commit_push(self.state_dir, "dev", "idle")
        self.assertFalse(success)
        self.assertIn("git not found", err)


class CreateCheckpointPropagatesGitPushedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.transcript_path = os.path.join(self._tmp.name, "t.jsonl")
        with open(self.transcript_path, "w") as f:
            f.write(json.dumps({"message": {"role": "user", "content": "hi"}}) + "\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, git_pushed, git_push_error=""):
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value={
                "task": "t", "discussion_summary": "", "accomplishments": [], "in_progress": [],
                "next_actions": [], "decisions": [], "user_rejected_decisions": [],
                "failed_approaches": [], "files_in_play": [], "relational_files": [],
                "uncommitted_files": [], "blockers": [], "completed_goals": [],
                "session_metadata": {"trigger_type": "idle", "timestamp": "2026-07-16T00:00:00Z"},
             }), \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push", return_value=(git_pushed, git_push_error)), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            return checkpoint.create_checkpoint(
                trigger_type="idle", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
            )

    def test_successful_push_reflected_in_result(self):
        result = self._run(True)
        self.assertTrue(result["git_pushed"])
        self.assertEqual(result["git_push_error"], "")

    def test_failed_push_reflected_in_result(self):
        result = self._run(False, "fatal: could not resolve host")
        self.assertFalse(result["git_pushed"])
        self.assertEqual(result["git_push_error"], "fatal: could not resolve host")


class IdleCheckpointVoiceHonestyTests(unittest.TestCase):
    """The bug the user actually reported: voice claims 'state saved to git' at
    the 10-minute idle mark regardless of whether the push worked."""

    def test_speaks_success_message_when_pushed(self):
        with patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.checkpoint.create_checkpoint", return_value={"git_pushed": True, "trigger": "idle"}), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch.object(lifecycle, "_speak") as mock_speak, \
             tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            lifecycle._execute_idle_checkpoint({}, tmp)

        mock_speak.assert_called_once()
        msg = mock_speak.call_args[0][0]
        self.assertIn("state saved to git", msg)
        self.assertNotIn("failed", msg.lower())

    def test_speaks_failure_message_when_push_failed(self):
        with patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.checkpoint.create_checkpoint",
                   return_value={"git_pushed": False, "git_push_error": "no network", "trigger": "idle"}), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch.object(lifecycle, "_speak") as mock_speak, \
             tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            lifecycle._execute_idle_checkpoint({}, tmp)

        mock_speak.assert_called_once()
        msg = mock_speak.call_args[0][0]
        self.assertNotIn("state saved to git", msg)
        self.assertIn("failed", msg.lower())


class WriteNotificationHonestyTests(unittest.TestCase):
    def test_context_trigger_success_message(self):
        with patch.object(lifecycle, "_speak") as mock_speak, \
             patch.object(lifecycle, "_NOTIFICATION_PATH", os.path.join(tempfile.mkdtemp(), "n.json")):
            lifecycle._write_notification("context", pct=0.9, git_pushed=True)
        msg = mock_speak.call_args[0][0]
        self.assertIn("state saved to git", msg)

    def test_context_trigger_failure_message(self):
        with patch.object(lifecycle, "_speak") as mock_speak, \
             patch.object(lifecycle, "_NOTIFICATION_PATH", os.path.join(tempfile.mkdtemp(), "n.json")):
            lifecycle._write_notification("context", pct=0.9, git_pushed=False)
        msg = mock_speak.call_args[0][0]
        self.assertNotIn("state saved to git", msg)
        self.assertIn("FAILED", msg)

    def test_quota_trigger_failure_message(self):
        with patch.object(lifecycle, "_speak") as mock_speak, \
             patch.object(lifecycle, "_NOTIFICATION_PATH", os.path.join(tempfile.mkdtemp(), "n.json")):
            lifecycle._write_notification("quota", pct=91, git_pushed=False)
        msg = mock_speak.call_args[0][0]
        self.assertNotIn("state saved to git", msg)
        self.assertIn("FAILED", msg)


if __name__ == "__main__":
    unittest.main()
