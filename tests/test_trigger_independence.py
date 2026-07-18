"""
Regression tests for the trigger-independence fix (2026-07-16).

context/quota/idle used to be one if/elif/elif chain in run_daemon()'s
per-session evaluation — the FIRST matching branch won and every branch
after it was skipped for the whole cycle. Context trips at 60%, far below
quota's 90% or any real idle gap, so in any real working session context
fires first, marks the session "already_companioned", and that first branch
matches forever afterward. Confirmed in production: a session sat "already
has a companion open" for 24+ hours while quota climbed from 57% to 89%
underneath it — Trigger B never once evaluated.

_evaluate_session_triggers() now runs three independent if-blocks (not
elif-chained to each other) with per-trigger-type cooldown keys, extracted
out of run_daemon()'s infinite loop specifically so this is testable at all.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


def _stats(**overrides):
    base = {
        "project_path": "/fake/project",
        "session_id": "sess123",
        "context_pct": 0.0,
        "context_label": "ok",
        "quota_pct": None,
        "quota_reset_at": "",
    }
    base.update(overrides)
    return base


class TriggerIndependenceTests(unittest.TestCase):
    def setUp(self):
        # Neutralize everything _evaluate_session_triggers touches outside its
        # own explicit state-dict parameters, so each test only exercises the
        # branch logic itself.
        patches = [
            patch.object(lifecycle, "_log"),
            patch.object(lifecycle, "_speak"),
            patch.object(lifecycle, "_save_companioned_sessions"),
            patch.object(lifecycle, "_save_trigger_state"),
            patch.object(lifecycle, "_save_quota_triggered_windows"),
            patch.object(lifecycle, "_save_quota_warned_windows"),
            patch.object(lifecycle, "_save_idle_triggered"),
            patch.object(lifecycle, "_last_turn_stop", return_value=(None, 0)),
            patch.object(lifecycle, "_turn_currently_active", return_value=False),
            patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[111]),
            patch("askr.session.model_windows.ensure_cached"),
        ]
        self._mocks = {p.attribute: p.start() for p in patches}
        self.addCleanup(lambda: [p.stop() for p in patches])

        thread_patch = patch.object(lifecycle.threading, "Thread")
        self.mock_thread_cls = thread_patch.start()
        self.addCleanup(thread_patch.stop)
        self.mock_thread = MagicMock()
        self.mock_thread_cls.return_value = self.mock_thread

    def _thread_targets(self):
        return [call.kwargs.get("target") for call in self.mock_thread_cls.call_args_list]

    def test_quota_fires_even_when_context_already_companioned(self):
        """The core bug: a session already past CONTEXT_TRIGGER and already
        companioned must NOT block quota from firing once it crosses 90%."""
        stats = _stats(
            context_pct=0.70,  # above CONTEXT_TRIGGER (0.60), already companioned below
            quota_pct=95.0,
            quota_reset_at="2026-01-01T00:00:00Z",
        )
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={"sess123": 0.0},
            quota_warned_windows=set(),
            companioned_sessions={"sess123"},  # already companioned for context
            last_trigger_at={},
            quota_triggered_windows=set(),
            idle_triggered={},
        )
        self.assertIn(lifecycle._execute_trigger, self._thread_targets())

    def test_idle_fires_even_when_context_already_companioned(self):
        """Same bug, idle side: point 2 from the design conversation — a session
        left unattended for 10 minutes must still get its idle checkpoint even
        though it already has a companion open for context."""
        stats = _stats(context_pct=0.70)
        with patch.object(lifecycle, "_last_turn_stop", return_value=(12345.0, lifecycle.IDLE_TRIGGER_SECS + 5)):
            lifecycle._evaluate_session_triggers(
                stats,
                session_first_seen={"sess123": 0.0},
                quota_warned_windows=set(),
                companioned_sessions={"sess123"},
                last_trigger_at={},
                quota_triggered_windows=set(),
                idle_triggered={},
            )
        self.assertIn(lifecycle._execute_idle_checkpoint, self._thread_targets())

    def test_context_and_quota_can_both_fire_in_the_same_call(self):
        """Not elif-chained: a brand-new session crossing both thresholds at
        once should fire both, not just whichever came first in the chain."""
        stats = _stats(
            context_pct=0.65,
            quota_pct=92.0,
            quota_reset_at="2026-01-01T00:00:00Z",
        )
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={"sess123": 0.0},
            quota_warned_windows=set(),
            companioned_sessions=set(),  # not yet companioned
            last_trigger_at={},
            quota_triggered_windows=set(),
            idle_triggered={},
        )
        targets = self._thread_targets()
        self.assertIn(lifecycle._open_companion_session_for_trigger, targets)
        self.assertIn(lifecycle._execute_trigger, targets)

    def test_context_cooldown_does_not_block_quota(self):
        """Per-trigger-type cooldown keys: context being in its own cooldown
        window must not prevent quota's independent cooldown from allowing it
        to fire."""
        import time
        stats = _stats(
            context_pct=0.65,
            quota_pct=93.0,
            quota_reset_at="2026-01-01T00:00:00Z",
        )
        last_trigger_at = {"/fake/project::context": time.time()}  # context just fired, in cooldown
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={"sess123": 0.0},
            quota_warned_windows=set(),
            companioned_sessions=set(),
            last_trigger_at=last_trigger_at,
            quota_triggered_windows=set(),
            idle_triggered={},
        )
        self.assertIn(lifecycle._execute_trigger, self._thread_targets())

    def test_quota_already_fired_for_window_does_not_refire(self):
        stats = _stats(quota_pct=95.0, quota_reset_at="2026-01-01T00:00:00Z")
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={"sess123": 0.0},
            quota_warned_windows=set(),
            companioned_sessions=set(),
            last_trigger_at={},
            quota_triggered_windows={"2026-01-01T00:00:00Z"},
            idle_triggered={},
        )
        self.assertNotIn(lifecycle._execute_trigger, self._thread_targets())

    def test_quota_without_reset_at_skips_rather_than_firing_blind(self):
        stats = _stats(quota_pct=95.0, quota_reset_at="")
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={"sess123": 0.0},
            quota_warned_windows=set(),
            companioned_sessions=set(),
            last_trigger_at={},
            quota_triggered_windows=set(),
            idle_triggered={},
        )
        self.assertNotIn(lifecycle._execute_trigger, self._thread_targets())

    def test_activity_grace_period_skips_all_triggers(self):
        import time
        stats = _stats(context_pct=0.90, quota_pct=99.0, quota_reset_at="x")
        lifecycle._evaluate_session_triggers(
            stats,
            session_first_seen={},  # not seen before -> first_seen = now
            quota_warned_windows=set(),
            companioned_sessions=set(),
            last_trigger_at={},
            quota_triggered_windows=set(),
            idle_triggered={},
        )
        self.mock_thread_cls.assert_not_called()

    def test_missing_project_path_is_skipped_not_guessed(self):
        stats = _stats(project_path=None)
        # Must not raise, must not fire anything.
        lifecycle._evaluate_session_triggers(
            stats, {}, set(), set(), {}, set(), {},
        )
        self.mock_thread_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
