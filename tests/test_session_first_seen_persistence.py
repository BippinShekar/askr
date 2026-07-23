"""
Regression test for the session_first_seen persistence fix (2026-07-23).

session_first_seen used to be a plain in-memory dict created fresh in
run_daemon() — session_id -> epoch first observed, gating ACTIVITY_GRACE_SECS
(60s) before any trigger (context/quota/idle) is evaluated for that session.
daemon.log confirmed the daemon self-restarts on every source-file change
("source files updated — exiting for launchd restart"), and during active
development these restarts recurred faster than 60s apart. Since the dict
wasn't disk-backed, every restart reset every active session's "first
observed" clock back to zero — so a session could sit in the grace period
forever, with NONE of its triggers ever evaluated, no matter how high its
context or quota climbed. Confirmed as the likely explanation for a real
incident: a session at 93% context with no companion ever opened.

Fixed by persisting session_first_seen the same way trigger_state and
companioned_sessions already are: loaded at daemon startup, saved the first
time a session_id is observed.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class SessionFirstSeenPersistenceTests(unittest.TestCase):
    def test_save_then_load_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sfs.json")
            with patch.object(lifecycle, "_SESSION_FIRST_SEEN_PATH", path):
                lifecycle._save_session_first_seen({"sess-a": 123.0})
                result = lifecycle._load_session_first_seen()
        self.assertEqual(result, {"sess-a": 123.0})

    def test_load_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "does_not_exist.json")
            with patch.object(lifecycle, "_SESSION_FIRST_SEEN_PATH", path):
                result = lifecycle._load_session_first_seen()
        self.assertEqual(result, {})

    def test_prune_drops_entries_older_than_a_day(self):
        import time
        now = time.time()
        first_seen = {"stale": now - 90000, "fresh": now - 10}
        result = lifecycle._prune_session_first_seen(first_seen)
        self.assertEqual(result, {"fresh": now - 10})

    def test_restart_does_not_reset_a_session_already_past_grace(self):
        """The actual bug: simulate a daemon restart by loading a fresh dict
        from disk (as run_daemon() now does) where this session_id was
        already observed well over ACTIVITY_GRACE_SECS ago. Trigger
        evaluation must proceed past the grace check, not restart the
        clock — this is what was broken when the dict was in-memory-only."""
        import time
        session_id = "sess-already-past-grace"
        long_ago = time.time() - (lifecycle.ACTIVITY_GRACE_SECS + 30)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "sfs.json")
            with patch.object(lifecycle, "_SESSION_FIRST_SEEN_PATH", path):
                lifecycle._save_session_first_seen({session_id: long_ago})
                # Simulate what run_daemon() does after a restart: load from disk
                # instead of starting a fresh {}.
                restarted_first_seen = lifecycle._load_session_first_seen()

        with patch.object(lifecycle, "_log") as mock_log, \
             patch.object(lifecycle, "_speak"), \
             patch.object(lifecycle, "_save_companioned_sessions"), \
             patch.object(lifecycle, "_save_trigger_state"), \
             patch.object(lifecycle, "_save_quota_triggered_windows"), \
             patch.object(lifecycle, "_save_quota_warned_windows"), \
             patch.object(lifecycle, "_save_idle_triggered"), \
             patch.object(lifecycle, "_save_session_first_seen"), \
             patch.object(lifecycle, "_last_turn_stop", return_value=(None, 0)), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]), \
             patch("askr.session.model_windows.ensure_cached"), \
             patch.object(lifecycle.threading, "Thread"):
            lifecycle._evaluate_session_triggers(
                {
                    "project_path": "/fake/project",
                    "session_id": session_id,
                    "context_pct": 0.0,
                    "context_label": "ok",
                    "quota_pct": None,
                    "quota_reset_at": "",
                },
                restarted_first_seen,
                set(), set(), {}, set(), {},
            )

        grace_logs = [
            call.args[0] for call in mock_log.call_args_list
            if call.args and "activity grace period" in call.args[0]
        ]
        self.assertEqual(grace_logs, [])


if __name__ == "__main__":
    unittest.main()
