"""
Tests for the quota three-phase split (2026-07-16): checkpoint the instant
the turn genuinely finishes (no UX grace), silently wait for the REAL account
quota to be near-exhausted (not the 90% trigger threshold), only then
surface the companion + voice.

Two problems this fixes, both from the design conversation:
1. _wait_for_turn_to_finish's 90s/600s wait was gating the checkpoint itself
   — a user who reads-and-replies within 90 seconds (normal, fast usage)
   could keep quota climbing unchecked through the real 100% wall while
   nothing had been saved yet. require_quiet_grace=False on the checkpoint's
   wait removes the UX-only grace period, keeping only the correctness-
   required "turn has genuinely stopped" condition.
2. The reassurance used to fire right at the 90% trigger threshold, cutting
   the user off ~10% of their remaining quota early for no reason. It now
   waits (silently, without disturbing the user) until real quota reads
   QUOTA_NOTIFY_TRIGGER or the reset has already passed.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class WaitForTurnToFinishFastPathTests(unittest.TestCase):
    """require_quiet_grace=False must not require TURN_QUIET_GRACE_SECS of
    silence — only that the turn has genuinely stopped."""

    def test_fast_path_does_not_wait_for_quiet_grace(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop", return_value=(123.0, 3)), \
             patch("askr.session.checkpoint.has_outstanding_subagent", return_value=False), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch.object(lifecycle.time, "sleep"):
            # stop_idle_secs=3, far below TURN_QUIET_GRACE_SECS (90) — the slow
            # path would keep waiting; the fast path must return immediately.
            result = lifecycle._wait_for_turn_to_finish("/fake", "sess", require_quiet_grace=False)
        self.assertTrue(result)

    def test_slow_path_keeps_polling_when_not_yet_quiet_yet_stops_once_grace_met(self):
        """require_quiet_grace=True (the default, used by the context trigger)
        must not finish on the first poll if stop_idle_secs is still below
        TURN_QUIET_GRACE_SECS — only the fast path (require_quiet_grace=False)
        is allowed to return on turn-stopped alone. MAX_WAIT_SECS is a local
        constant (600s), too long to actually run in a test, so this drives
        the loop via side_effect: first call reports 3s of quiet (not enough),
        second call reports enough — proving the grace period is genuinely
        being enforced rather than skipped."""
        stop_reports = iter([(123.0, 3), (123.0, lifecycle.TURN_QUIET_GRACE_SECS + 1)])
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop", side_effect=lambda *_: next(stop_reports)), \
             patch("askr.session.checkpoint.has_outstanding_subagent", return_value=False), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch.object(lifecycle.time, "sleep"):
            result = lifecycle._wait_for_turn_to_finish("/fake", "sess", require_quiet_grace=True)
        self.assertTrue(result)
        # Consumed exactly the two prepared reports — did not stop on the
        # first (insufficiently-quiet) one.
        self.assertRaises(StopIteration, lambda: next(stop_reports))


class WaitUntilQuotaNearExhaustedTests(unittest.TestCase):
    def test_returns_immediately_if_reset_already_passed(self):
        past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        with patch("askr.session.usage_api.get_quota_status") as mock_status, \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            lifecycle._wait_until_quota_near_exhausted(past)
        mock_status.assert_not_called()
        mock_sleep.assert_not_called()

    def test_returns_immediately_if_quota_already_near_exhausted(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        status = MagicMock(five_hour_pct=lifecycle.QUOTA_NOTIFY_TRIGGER + 0.5)
        with patch("askr.session.usage_api.get_quota_status", return_value=status), \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            lifecycle._wait_until_quota_near_exhausted(future)
        mock_sleep.assert_not_called()

    def test_polls_until_near_exhausted(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        below = MagicMock(five_hour_pct=91.0)
        above = MagicMock(five_hour_pct=lifecycle.QUOTA_NOTIFY_TRIGGER + 1)
        with patch("askr.session.usage_api.get_quota_status", side_effect=[below, below, above]), \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            lifecycle._wait_until_quota_near_exhausted(future)
        self.assertEqual(mock_sleep.call_count, 2)  # slept twice, then saw "above" and returned

    def test_unparseable_reset_time_fails_open_without_blocking(self):
        with patch("askr.session.usage_api.get_quota_status") as mock_status, \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            lifecycle._wait_until_quota_near_exhausted("not-a-real-timestamp")
        mock_status.assert_not_called()
        mock_sleep.assert_not_called()


class ExecuteQuotaTriggerPhaseOrderTests(unittest.TestCase):
    """Confirms the checkpoint (phase 1) happens before the notify (phase 3),
    and that the near-exhausted wait (phase 2) sits between them — the actual
    bug being fixed was notify happening immediately after a slow checkpoint,
    with no phase 2 at all."""

    def test_checkpoint_precedes_notify_and_near_exhausted_wait_runs_between(self):
        call_order = []

        def record(name):
            def _inner(*a, **kw):
                call_order.append(name)
                if name == "create_checkpoint":
                    return {"trigger": "quota", "timestamp": "2026-01-01T00:00:00Z", "handover_path": "", "git_pushed": True}
                return None
            return _inner

        with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch.object(lifecycle, "_wait_for_turn_to_finish", side_effect=record("wait_for_turn")), \
             patch("os.path.isdir", return_value=True), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch("askr.session.checkpoint.create_checkpoint", side_effect=record("create_checkpoint")), \
             patch.object(lifecycle, "_wait_until_quota_near_exhausted", side_effect=record("near_exhausted_wait")), \
             patch.object(lifecycle, "_get_next_goal", return_value=""), \
             patch.object(lifecycle, "_write_launch_mode"), \
             patch.object(lifecycle, "_write_notification", side_effect=record("notify")), \
             patch.object(lifecycle, "_wait_for_reset", side_effect=record("wait_for_reset")), \
             patch.object(lifecycle, "_start_claude", return_value=False):
            lifecycle._execute_quota_trigger(
                {"quota_pct": 95.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )

        self.assertEqual(
            call_order,
            ["wait_for_turn", "create_checkpoint", "near_exhausted_wait", "notify", "wait_for_reset"],
        )

    def test_checkpoint_wait_uses_no_quiet_grace(self):
        with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch.object(lifecycle, "_wait_for_turn_to_finish") as mock_wait, \
             patch("os.path.isdir", return_value=True), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch("askr.session.checkpoint.create_checkpoint",
                   return_value={"trigger": "quota", "timestamp": "", "handover_path": "", "git_pushed": True}), \
             patch.object(lifecycle, "_wait_until_quota_near_exhausted"), \
             patch.object(lifecycle, "_get_next_goal", return_value=""), \
             patch.object(lifecycle, "_write_launch_mode"), \
             patch.object(lifecycle, "_write_notification"), \
             patch.object(lifecycle, "_wait_for_reset"), \
             patch.object(lifecycle, "_start_claude", return_value=False):
            lifecycle._execute_quota_trigger(
                {"quota_pct": 95.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )
        mock_wait.assert_called_once_with("/fake/project", "sess123", require_quiet_grace=False)


if __name__ == "__main__":
    unittest.main()
