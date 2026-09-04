"""
Tests for the caffeinate-vs-quota-wait fix (2026-08-16).

Confirmed live 2026-08-15: Trigger B fired cleanly at quota=91.0%, but the
triggering session went idle 20 minutes later while _execute_quota_trigger's
background thread was still mid-wait. The idle transition unconditionally
called _stop_caffeinate(), the Mac slept, and the entire daemon (every
project, every thread) produced zero log output for 1h43m — including the
_wait_until_quota_near_exhausted poll loop, which needs to observe quota
crossing QUOTA_NOTIFY_TRIGGER (99%) in real time to ever surface a warning,
notification, or voice announcement. It woke up only after the real reset
had already passed, so the "near exhausted, notifying" branch never ran and
nothing reached the user live.

_stop_caffeinate() must now refuse to release the sleep lock while any
_execute_quota_trigger call (Phase 2 wait or the Stage 5 premature-activity
watch that follows it) is still in flight, regardless of session idle state.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class QuotaWaitDepthTests(unittest.TestCase):
    def setUp(self):
        lifecycle._quota_wait_depth = 0

    def tearDown(self):
        lifecycle._quota_wait_depth = 0

    def test_begin_end_round_trips_to_zero(self):
        self.assertFalse(lifecycle._quota_wait_in_flight())
        lifecycle._quota_wait_begin()
        self.assertTrue(lifecycle._quota_wait_in_flight())
        lifecycle._quota_wait_end()
        self.assertFalse(lifecycle._quota_wait_in_flight())

    def test_two_concurrent_projects_both_tracked(self):
        # Quota is account-wide but _evaluate_session_triggers runs per
        # project — two projects can each have their own in-flight wait.
        lifecycle._quota_wait_begin()
        lifecycle._quota_wait_begin()
        self.assertTrue(lifecycle._quota_wait_in_flight())
        lifecycle._quota_wait_end()
        self.assertTrue(lifecycle._quota_wait_in_flight())
        lifecycle._quota_wait_end()
        self.assertFalse(lifecycle._quota_wait_in_flight())

    def test_end_never_goes_negative(self):
        lifecycle._quota_wait_end()
        lifecycle._quota_wait_end()
        self.assertFalse(lifecycle._quota_wait_in_flight())

    def test_wrapper_ends_tracking_even_if_impl_raises(self):
        with patch.object(lifecycle, "_execute_quota_trigger_impl", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                lifecycle._execute_quota_trigger({}, "/fake/project", "sess")
        self.assertFalse(lifecycle._quota_wait_in_flight())

    def test_wrapper_tracks_depth_during_impl_call(self):
        observed = {}

        def fake_impl(stats, project_path, session_id):
            observed["in_flight"] = lifecycle._quota_wait_in_flight()

        with patch.object(lifecycle, "_execute_quota_trigger_impl", side_effect=fake_impl):
            lifecycle._execute_quota_trigger({}, "/fake/project", "sess")
        self.assertTrue(observed["in_flight"])
        self.assertFalse(lifecycle._quota_wait_in_flight())


class StopCaffeinateGuardTests(unittest.TestCase):
    def setUp(self):
        lifecycle._quota_wait_depth = 0

    def tearDown(self):
        lifecycle._quota_wait_depth = 0

    def test_stop_caffeinate_skipped_while_quota_wait_in_flight(self):
        lifecycle._quota_wait_begin()
        with patch.object(lifecycle, "_caffeinate_running", return_value=True) as running, \
             patch("os.kill") as kill:
            lifecycle._stop_caffeinate()
        running.assert_not_called()
        kill.assert_not_called()

    def test_stop_caffeinate_proceeds_once_quota_wait_clears(self):
        lifecycle._quota_wait_begin()
        lifecycle._quota_wait_end()
        with patch.object(lifecycle, "_caffeinate_running", return_value=False) as running:
            lifecycle._stop_caffeinate()
        running.assert_called_once()


class SourceRestartGuardTests(unittest.TestCase):
    """
    2026-09-05: the daemon's source-file self-watch (run_daemon()'s
    "source files updated — exiting for launchd restart" -> sys.exit(0))
    used to fire unconditionally, same as any other restart trigger — but
    _execute_quota_trigger's Escape/wait/cont sequence runs on a daemon=True
    background thread with no persisted state; sys.exit(0) kills it
    instantly mid-wait, silently abandoning it with no fallback ever firing.
    Live-reproduced: a quota-wait thread was mid-flight while lifecycle.py
    was being edited; nothing in the restart path checked for that.

    run_daemon()'s main loop isn't directly unit-testable (see
    test_trigger_independence.py's docstring on why _evaluate_session_triggers
    had to be extracted) — this instead pins the source itself, matching the
    project's precedent for asserting an unextracted call site wasn't
    reverted (see test_session_scoped_transcript.py's thread-args check).
    """

    def test_source_restart_branch_checks_quota_wait_in_flight(self):
        import inspect
        src = inspect.getsource(lifecycle.run_daemon)
        self.assertIn(
            "if _max_source_mtime() > _STARTUP_SOURCE_MTIME and _quota_wait_in_flight():",
            src,
        )
        self.assertIn("deferring the restart until it finishes", src)


if __name__ == "__main__":
    unittest.main()
