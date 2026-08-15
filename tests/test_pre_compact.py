"""
Tests for askr/hooks/pre_compact.py's kill-fast reorder (2026-08-08).

Root bug this fixes: the emergency path used to run the full heavy checkpoint
(LLM handover call, architecture regen, git push, Discord webhook) BEFORE
sending SIGTERM — slow enough that Claude Code's own compaction routinely
finished first, defeating the whole mechanism. The kill must now be the
first thing that happens once a PID is found, with the heavy checkpoint,
notification, and companion-open all deferred to run after it.

Covers: kill-before-heavy-work ordering, the no-pid synchronous fallback,
per-session notify/speak dedup (not a time cooldown), session duration
estimation, and _finish_emergency_checkpoint's notify/companion-open logic.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import pre_compact


# ---------------------------------------------------------------------------
# Per-session notify dedup
# ---------------------------------------------------------------------------

class NotifiedSessionsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_path = pre_compact._NOTIFIED_SESSIONS_PATH
        pre_compact._NOTIFIED_SESSIONS_PATH = os.path.join(self._tmp.name, "notified.json")

    def tearDown(self):
        pre_compact._NOTIFIED_SESSIONS_PATH = self._orig_path
        self._tmp.cleanup()

    def test_missing_file_returns_empty_set(self):
        self.assertEqual(pre_compact._load_notified_sessions(), set())

    def test_mark_then_load_contains_session(self):
        pre_compact._mark_session_notified("sess-1")
        self.assertIn("sess-1", pre_compact._load_notified_sessions())

    def test_mark_empty_session_id_is_noop(self):
        pre_compact._mark_session_notified("")
        self.assertEqual(pre_compact._load_notified_sessions(), set())

    def test_multiple_sessions_accumulate(self):
        pre_compact._mark_session_notified("sess-1")
        pre_compact._mark_session_notified("sess-2")
        sessions = pre_compact._load_notified_sessions()
        self.assertIn("sess-1", sessions)
        self.assertIn("sess-2", sessions)


# ---------------------------------------------------------------------------
# _session_duration_minutes — pure function over a transcript file
# ---------------------------------------------------------------------------

class SessionDurationTests(unittest.TestCase):
    def _write_transcript(self, entries):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        for e in entries:
            f.write(json.dumps(e) + "\n")
        f.close()
        return f.name

    def test_computes_span_in_minutes(self):
        path = self._write_transcript([
            {"timestamp": "2026-08-08T10:00:00Z"},
            {"timestamp": "2026-08-08T10:15:00Z"},
        ])
        try:
            self.assertEqual(pre_compact._session_duration_minutes(path), 15)
        finally:
            os.remove(path)

    def test_missing_file_returns_zero(self):
        self.assertEqual(pre_compact._session_duration_minutes("/nonexistent/path.jsonl"), 0)

    def test_no_timestamps_returns_zero(self):
        path = self._write_transcript([{"foo": "bar"}])
        try:
            self.assertEqual(pre_compact._session_duration_minutes(path), 0)
        finally:
            os.remove(path)

    def test_malformed_lines_skipped_not_raised(self):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        f.write("not json\n")
        f.write(json.dumps({"timestamp": "2026-08-08T10:00:00Z"}) + "\n")
        f.write(json.dumps({"timestamp": "2026-08-08T10:05:00Z"}) + "\n")
        f.close()
        try:
            self.assertEqual(pre_compact._session_duration_minutes(f.name), 5)
        finally:
            os.remove(f.name)


# ---------------------------------------------------------------------------
# main() — kill must happen before any heavy work is even scheduled
# ---------------------------------------------------------------------------

class MainKillOrderingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self._orig_stdin = sys.stdin

    def tearDown(self):
        sys.stdin = self._orig_stdin
        self._tmp.cleanup()

    def _feed(self, payload):
        sys.stdin = json.dumps(payload)
        import io
        sys.stdin = io.StringIO(json.dumps(payload))

    def test_pid_found_kills_before_spawning_background_work(self):
        call_order = []

        with patch("askr.state.config.get_state_dir", return_value=self.state_dir), \
             patch("askr.hooks.pre_compact.load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=self._tmp.name), \
             patch("askr.hooks.pre_compact._find_session_pid", return_value=4242), \
             patch("askr.session.lifecycle._find_all_claude_pids_by_project", return_value=[4242]), \
             patch("askr.session.monitor.stats_path_for_session", return_value="/nonexistent"), \
             patch("os.kill", side_effect=lambda pid, sig: call_order.append(("kill", pid))) as mock_kill, \
             patch("askr.hooks.pre_compact._spawn_background_finish",
                   side_effect=lambda *a, **k: call_order.append("spawn_background")) as mock_spawn, \
             patch("askr.hooks.pre_compact.create_checkpoint" if False else "os.path.exists", return_value=False):
            self._feed({"transcript_path": "/tmp/fake-session.jsonl"})
            pre_compact.main()

        mock_kill.assert_called_once_with(4242, __import__("signal").SIGKILL)
        mock_spawn.assert_called_once()
        self.assertEqual(call_order, [("kill", 4242), "spawn_background"])

    def test_no_pid_runs_checkpoint_synchronously_and_never_spawns_background(self):
        with patch("askr.state.config.get_state_dir", return_value=self.state_dir), \
             patch("askr.hooks.pre_compact.load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=self._tmp.name), \
             patch("askr.hooks.pre_compact._find_session_pid", return_value=None), \
             patch("askr.session.checkpoint.create_checkpoint", return_value={"git_pushed": True}) as mock_ckpt, \
             patch("askr.hooks.pre_compact._spawn_background_finish") as mock_spawn:
            self._feed({"transcript_path": "/tmp/fake-session.jsonl"})
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                pre_compact.main()

        mock_ckpt.assert_called_once()
        mock_spawn.assert_not_called()
        out = json.loads(buf.getvalue())
        self.assertIn("resume from the handover", out["custom_instructions"])

    def test_second_fire_for_same_session_still_kills_and_spawns_background(self):
        # Per-session dedup gates the notify/speak inside _finish_emergency_checkpoint,
        # never the kill+spawn in main() — the safety action must run every time.
        with patch("askr.state.config.get_state_dir", return_value=self.state_dir), \
             patch("askr.hooks.pre_compact.load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=self._tmp.name), \
             patch("askr.hooks.pre_compact._find_session_pid", return_value=4242), \
             patch("askr.session.lifecycle._find_all_claude_pids_by_project", return_value=[4242]), \
             patch("os.kill") as mock_kill, \
             patch("askr.hooks.pre_compact._spawn_background_finish") as mock_spawn:
            self._feed({"transcript_path": "/tmp/repeat-session.jsonl"})
            pre_compact._mark_session_notified("repeat-session")
            pre_compact.main()

        mock_kill.assert_called_once()
        mock_spawn.assert_called_once()
        # already_notified=True must be threaded through as the 6th positional arg
        args = mock_spawn.call_args[0]
        self.assertTrue(args[5])


# ---------------------------------------------------------------------------
# Terminal mouse-tracking reset after SIGKILL (2026-08-16)
#
# SIGKILL gives Claude Code's TUI no chance to disable the xterm mouse-
# tracking mode it enables on start, so every mouse move over that terminal
# afterward gets SGR-encoded and dumped onto the screen as garbage text.
# ---------------------------------------------------------------------------

class TerminalResetTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self._orig_stdin = sys.stdin

    def tearDown(self):
        sys.stdin = self._orig_stdin
        self._tmp.cleanup()

    def _feed(self, payload):
        import io
        sys.stdin = io.StringIO(json.dumps(payload))

    def test_get_tty_for_pid_parses_ps_output(self):
        with patch("subprocess.run", return_value=MagicMock(stdout="ttys003\n")):
            self.assertEqual(pre_compact._get_tty_for_pid(4242), "ttys003")

    def test_get_tty_for_pid_returns_none_for_no_tty(self):
        with patch("subprocess.run", return_value=MagicMock(stdout="??\n")):
            self.assertIsNone(pre_compact._get_tty_for_pid(4242))

    def test_get_tty_for_pid_returns_none_on_error(self):
        with patch("subprocess.run", side_effect=OSError("boom")):
            self.assertIsNone(pre_compact._get_tty_for_pid(4242))

    def test_reset_terminal_mouse_tracking_writes_disable_sequence(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            pre_compact._reset_terminal_mouse_tracking(tmp.name)
            with open(tmp.name) as f:
                written = f.read()
            self.assertIn("\x1b[?1000l", written)
            self.assertIn("\x1b[?1006l", written)
            self.assertIn("\x1b[?25h", written)
        finally:
            os.remove(tmp.name)

    def test_reset_terminal_mouse_tracking_never_raises_on_bad_device(self):
        pre_compact._reset_terminal_mouse_tracking("/nonexistent/path/ttyXXX")

    def test_main_resolves_tty_before_kill_and_resets_after(self):
        call_order = []
        with patch("askr.state.config.get_state_dir", return_value=self.state_dir), \
             patch("askr.hooks.pre_compact.load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=self._tmp.name), \
             patch("askr.hooks.pre_compact._find_session_pid", return_value=4242), \
             patch("askr.session.lifecycle._find_all_claude_pids_by_project", return_value=[4242]), \
             patch("askr.hooks.pre_compact._get_tty_for_pid",
                   side_effect=lambda pid: (call_order.append("get_tty"), "ttys003")[1]), \
             patch("os.kill", side_effect=lambda pid, sig: call_order.append("kill")), \
             patch("askr.hooks.pre_compact._reset_terminal_mouse_tracking",
                   side_effect=lambda tty: call_order.append("reset")) as mock_reset, \
             patch("askr.hooks.pre_compact._spawn_background_finish"):
            self._feed({"transcript_path": "/tmp/fake-session.jsonl"})
            pre_compact.main()

        self.assertEqual(call_order, ["get_tty", "kill", "reset"])
        mock_reset.assert_called_once_with("ttys003")

    def test_main_skips_reset_when_pid_has_no_tty(self):
        with patch("askr.state.config.get_state_dir", return_value=self.state_dir), \
             patch("askr.hooks.pre_compact.load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=self._tmp.name), \
             patch("askr.hooks.pre_compact._find_session_pid", return_value=4242), \
             patch("askr.session.lifecycle._find_all_claude_pids_by_project", return_value=[4242]), \
             patch("askr.hooks.pre_compact._get_tty_for_pid", return_value=None), \
             patch("os.kill"), \
             patch("askr.hooks.pre_compact._reset_terminal_mouse_tracking") as mock_reset, \
             patch("askr.hooks.pre_compact._spawn_background_finish"):
            self._feed({"transcript_path": "/tmp/fake-session.jsonl"})
            pre_compact.main()

        mock_reset.assert_not_called()


# ---------------------------------------------------------------------------
# _finish_emergency_checkpoint — notify/companion-open logic
# ---------------------------------------------------------------------------

class FinishEmergencyCheckpointTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_notified_path = pre_compact._NOTIFIED_SESSIONS_PATH
        pre_compact._NOTIFIED_SESSIONS_PATH = os.path.join(self._tmp.name, "notified.json")
        self._orig_pending_path = pre_compact._CHECKPOINT_PENDING
        pre_compact._CHECKPOINT_PENDING = os.path.join(self._tmp.name, "checkpoint_pending.json")

    def tearDown(self):
        pre_compact._NOTIFIED_SESSIONS_PATH = self._orig_notified_path
        pre_compact._CHECKPOINT_PENDING = self._orig_pending_path
        self._tmp.cleanup()

    def test_already_notified_skips_notification_and_speak(self):
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.hooks.pre_compact._speak") as mock_speak:
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=True, already_notified=True,
            )
        mock_speak.assert_not_called()

    def test_not_notified_writes_notification_and_speaks(self):
        notif_path = os.path.join(self._tmp.name, "notification.json")
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.session.lifecycle._NOTIFICATION_PATH", notif_path), \
             patch("askr.session.lifecycle._load_allowed_tools", return_value=[]), \
             patch("askr.hooks.pre_compact._speak") as mock_speak:
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=False, already_notified=False,
            )
        mock_speak.assert_called_once()
        with open(notif_path) as f:
            written = json.load(f)
        self.assertEqual(written["type"], "compaction_prevented")
        self.assertIn("switch to the companion", written["message"])

    def test_should_open_companion_true_spawns_terminal(self):
        notif_path = os.path.join(self._tmp.name, "notification.json")
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.session.lifecycle._NOTIFICATION_PATH", notif_path), \
             patch("askr.session.lifecycle._load_allowed_tools", return_value=[]), \
             patch("askr.session.lifecycle._spawn_terminal_app_fallback") as mock_spawn_term, \
             patch("askr.state.writer.append_event") as mock_event, \
             patch("askr.hooks.pre_compact._speak"):
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=True, already_notified=False,
            )
        mock_spawn_term.assert_called_once()
        mock_event.assert_called_once()
        self.assertEqual(mock_event.call_args[0][0], "companion_spawned")
        self.assertEqual(mock_event.call_args.kwargs["parent_session_id"], "sess-1")

    def test_empty_session_id_falls_back_to_transcript_path(self):
        """
        Regression test: every emergency companion_spawned event in production
        (2026-08-10 through 2026-08-15) shipped with parent_session_id "" even
        though transcript_path was always present — breaking askr graph's
        lineage for every emergency-spawned companion. session_id must be
        re-derived from transcript_path whenever it arrives empty.
        """
        notif_path = os.path.join(self._tmp.name, "notification.json")
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.session.lifecycle._NOTIFICATION_PATH", notif_path), \
             patch("askr.session.lifecycle._load_allowed_tools", return_value=[]), \
             patch("askr.session.lifecycle._spawn_terminal_app_fallback") as mock_spawn_term, \
             patch("askr.state.writer.append_event") as mock_event, \
             patch("askr.hooks.pre_compact._speak"):
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/8ed7cfb6-e562-430b-9c7c-3400745a8a51.jsonl", "",
                should_open_companion=True, already_notified=False,
            )
        mock_spawn_term.assert_called_once()
        mock_event.assert_called_once()
        self.assertEqual(
            mock_event.call_args.kwargs["parent_session_id"],
            "8ed7cfb6-e562-430b-9c7c-3400745a8a51",
        )

    def test_should_open_companion_false_does_not_spawn_terminal(self):
        notif_path = os.path.join(self._tmp.name, "notification.json")
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.session.lifecycle._NOTIFICATION_PATH", notif_path), \
             patch("askr.session.lifecycle._load_allowed_tools", return_value=[]), \
             patch("askr.session.lifecycle._spawn_terminal_app_fallback") as mock_spawn_term, \
             patch("askr.hooks.pre_compact._speak"):
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=False, already_notified=False,
            )
        mock_spawn_term.assert_not_called()

    def test_high_quota_writes_checkpoint_pending(self):
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 95, "context_pct": 0.5}), \
             patch("askr.hooks.pre_compact._speak"):
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=False, already_notified=True,
            )
        with open(pre_compact._CHECKPOINT_PENDING) as f:
            pending = json.load(f)
        self.assertEqual(pending["trigger"], "quota")
        self.assertEqual(pending["quota_pct"], 95)

    def test_low_quota_does_not_write_checkpoint_pending(self):
        with patch("askr.session.checkpoint.create_checkpoint", return_value={}), \
             patch("askr.hooks.pre_compact._latest_stats", return_value={"quota_pct": 10}), \
             patch("askr.hooks.pre_compact._speak"):
            pre_compact._finish_emergency_checkpoint(
                self._tmp.name, "dev", "/tmp/t.jsonl", "sess-1",
                should_open_companion=False, already_notified=True,
            )
        self.assertFalse(os.path.exists(pre_compact._CHECKPOINT_PENDING))


if __name__ == "__main__":
    unittest.main()
