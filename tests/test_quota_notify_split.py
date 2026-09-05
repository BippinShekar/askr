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
            result = lifecycle._wait_until_quota_near_exhausted(past)
        mock_status.assert_not_called()
        mock_sleep.assert_not_called()
        self.assertIsNone(result)

    def test_returns_immediately_if_quota_already_near_exhausted(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        status = MagicMock(five_hour_pct=lifecycle.QUOTA_NOTIFY_TRIGGER + 0.5)
        with patch("askr.session.usage_api.get_quota_status", return_value=status), \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            result = lifecycle._wait_until_quota_near_exhausted(future)
        mock_sleep.assert_not_called()
        self.assertEqual(result, lifecycle.QUOTA_NOTIFY_TRIGGER + 0.5)

    def test_polls_until_near_exhausted(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        below = MagicMock(five_hour_pct=91.0)
        above = MagicMock(five_hour_pct=lifecycle.QUOTA_NOTIFY_TRIGGER + 1)
        with patch("askr.session.usage_api.get_quota_status", side_effect=[below, below, above]), \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            result = lifecycle._wait_until_quota_near_exhausted(future)
        self.assertEqual(mock_sleep.call_count, 2)  # slept twice, then saw "above" and returned
        # The fresh, live-polled value — not the caller's stale trigger-time snapshot.
        self.assertEqual(result, lifecycle.QUOTA_NOTIFY_TRIGGER + 1)

    def test_unparseable_reset_time_fails_open_without_blocking(self):
        with patch("askr.session.usage_api.get_quota_status") as mock_status, \
             patch.object(lifecycle.time, "sleep") as mock_sleep:
            result = lifecycle._wait_until_quota_near_exhausted("not-a-real-timestamp")
        mock_status.assert_not_called()
        mock_sleep.assert_not_called()
        self.assertIsNone(result)


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
             patch.object(lifecycle, "_write_notification", side_effect=record("notify")):
            lifecycle._execute_quota_trigger(
                {"quota_pct": 95.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )

        # 2026-09-06: the trigger ends at the informational notification —
        # no terminal action, no wait-for-reset, no companion (Claude Code's
        # native auto-continue owns everything past this point now).
        self.assertEqual(
            call_order,
            ["wait_for_turn", "create_checkpoint", "near_exhausted_wait", "notify"],
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

    def test_announcement_uses_fresh_quota_not_stale_trigger_time_snapshot(self):
        """
        Confirmed live 2026-08-12: the stats dict _execute_quota_trigger
        receives is captured back when the trigger FIRST fired — Phase 1's
        checkpoint and Phase 2's own wait both take real time, so by Phase 3
        the account can already be well past that snapshot (a real instance:
        "Quota at 97%" was announced minutes after the account had already
        hit 100% and blocked). Phase 2 already re-polls the live API and
        knows the true number — Phase 3 must use that, not stats["quota_pct"].
        """
        with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch.object(lifecycle, "_wait_for_turn_to_finish"), \
             patch("os.path.isdir", return_value=True), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch("askr.session.checkpoint.create_checkpoint",
                   return_value={"trigger": "quota", "timestamp": "", "handover_path": "", "git_pushed": True}), \
             patch.object(lifecycle, "_wait_until_quota_near_exhausted", return_value=100.0), \
             patch.object(lifecycle, "_get_next_goal", return_value=""), \
             patch.object(lifecycle, "_write_launch_mode"), \
             patch.object(lifecycle, "_write_notification") as mock_notify, \
             patch.object(lifecycle, "_find_session_pid", return_value=None), \
             patch.object(lifecycle, "_wait_for_reset"), \
             patch.object(lifecycle, "_start_claude", return_value=False):
            lifecycle._execute_quota_trigger(
                # The stale snapshot the trigger fired on — must NOT be what
                # gets announced.
                {"quota_pct": 97.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )
        announced_pct = mock_notify.call_args[0][2]
        self.assertEqual(announced_pct, 100.0)

    def test_announcement_falls_back_to_stale_snapshot_when_no_fresh_reading(self):
        """When Phase 2 can't confirm a fresh value (unparseable reset time,
        reset already passed, API unreachable — all return None), Phase 3
        must still announce something rather than crashing or showing 0%."""
        with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
             patch("askr.state.config.load_developer", return_value="dev"), \
             patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")), \
             patch.object(lifecycle, "_wait_for_turn_to_finish"), \
             patch("os.path.isdir", return_value=True), \
             patch("askr.session.monitor._find_active_jsonl", return_value=""), \
             patch("askr.session.checkpoint.create_checkpoint",
                   return_value={"trigger": "quota", "timestamp": "", "handover_path": "", "git_pushed": True}), \
             patch.object(lifecycle, "_wait_until_quota_near_exhausted", return_value=None), \
             patch.object(lifecycle, "_get_next_goal", return_value=""), \
             patch.object(lifecycle, "_write_launch_mode"), \
             patch.object(lifecycle, "_write_notification") as mock_notify, \
             patch.object(lifecycle, "_find_session_pid", return_value=None), \
             patch.object(lifecycle, "_wait_for_reset"), \
             patch.object(lifecycle, "_start_claude", return_value=False):
            lifecycle._execute_quota_trigger(
                {"quota_pct": 97.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )
        announced_pct = mock_notify.call_args[0][2]
        self.assertEqual(announced_pct, 97.0)


class NoTerminalActionOnQuotaTriggerTests(unittest.TestCase):
    """
    2026-09-06: retires the 2026-08-12 same-session-resume feature (Escape ->
    watch -> "cont"). Confirmed live: Claude Code's CLI now natively handles
    the whole exhausted -> wait -> resume cycle on its own ("Usage limit
    reached ... continuing automatically" -> "Usage limit reset ...
    continuing automatically"), and the native prompt's "esc ... to cancel"
    wording means Escape now CANCELS that native auto-continue rather than
    selecting it (the 2026-08 binary analysis proving Escape == "wait for
    reset" was for an older Claude Code version). Live pattern that gave it
    away: every session askr sent Escape to got stuck; every session left
    untouched resumed on its own, right on schedule.

    _execute_quota_trigger_impl must now do exactly checkpoint + the
    informational "quota" notification, and nothing else — no terminal
    keystroke, no companion session, regardless of pid/ancestor/reset state.
    """

    def _base_patches(self, extra=None):
        patches = [
            patch.object(lifecycle, "_claude_cli_available", return_value=True),
            patch("askr.state.config.load_developer", return_value="dev"),
            patch("askr.session.safe_pause.is_safe_to_pause", return_value=(True, "")),
            patch.object(lifecycle, "_wait_for_turn_to_finish"),
            patch("os.path.isdir", return_value=True),
            patch("askr.session.monitor._find_active_jsonl", return_value="/fake/transcript.jsonl"),
            patch("askr.session.checkpoint.create_checkpoint",
                  return_value={"trigger": "quota", "timestamp": "", "handover_path": "", "git_pushed": True}),
            patch.object(lifecycle, "_wait_until_quota_near_exhausted"),
            patch.object(lifecycle, "_get_next_goal", return_value=""),
            patch.object(lifecycle, "_write_launch_mode"),
            patch.object(lifecycle, "_write_notification"),
            patch.object(lifecycle, "_notify_discord_resumed"),
            patch("askr.state.analytics.today_summary", return_value={"total_seconds": 0}),
            patch.object(lifecycle, "_write_resumed_marker"),
            patch("os.path.exists", return_value=True),
            patch("os.path.getmtime", return_value=100.0),
        ]
        return patches + (extra or [])

    def _run(self, extra_patches):
        with self._patch_stack(self._base_patches(extra_patches)):
            lifecycle._execute_quota_trigger(
                {"quota_pct": 100.0, "quota_reset_at": "2026-01-01T01:00:00Z"},
                "/fake/project", "sess123",
            )

    def _patch_stack(self, patches):
        from contextlib import ExitStack
        stack = ExitStack()
        for p in patches:
            stack.enter_context(p)
        return stack

    def test_no_terminal_action_sent_regardless_of_pid_resolution(self):
        """Even when pid/ancestor_pids resolve fine, no Escape and no 'cont'
        should ever be sent — Claude Code's native auto-continue owns this
        now, and touching the terminal at all is what broke it."""
        with patch.object(lifecycle, "_find_session_pid", return_value=4242), \
             patch.object(lifecycle, "_get_ancestor_pids", return_value=[100, 50]), \
             patch.object(lifecycle, "_watch_for_premature_activity") as mock_watch, \
             patch.object(lifecycle, "_write_terminal_action_notification") as mock_write_action, \
             patch.object(lifecycle, "_wait_for_reset") as mock_wait_reset, \
             patch.object(lifecycle, "_start_claude") as mock_start_claude, \
             patch.object(lifecycle, "_speak"):
            self._run([])

        mock_watch.assert_not_called()
        mock_write_action.assert_not_called()
        mock_wait_reset.assert_not_called()
        mock_start_claude.assert_not_called()

    def test_no_pid_still_sends_no_terminal_action_and_no_companion(self):
        with patch.object(lifecycle, "_find_session_pid", return_value=None), \
             patch.object(lifecycle, "_write_terminal_action_notification") as mock_write_action, \
             patch.object(lifecycle, "_wait_for_reset") as mock_wait_reset, \
             patch.object(lifecycle, "_start_claude") as mock_start_claude:
            self._run([])

        mock_write_action.assert_not_called()
        mock_wait_reset.assert_not_called()
        mock_start_claude.assert_not_called()


if __name__ == "__main__":
    unittest.main()
