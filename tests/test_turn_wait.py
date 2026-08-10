"""
Tests for lifecycle._wait_for_turn_to_finish's 2026-07-11 fix: a companion
session (or quota checkpoint) must not open the instant the ONE turn that
was active when the trigger fired ends — if the user immediately started a
new turn in that gap, opening then looks and feels identical to being
interrupted mid-reply. The wait must hold until there's a genuinely quiet
moment: the triggering turn stopped AND no new turn is currently active.

Also covers the 2026-07-13 fix (no outstanding Agent-tool subagent) and the
2026-07-14 fix (TURN_QUIET_GRACE_SECS of real silence since Stop) — a
plain-text question at the end of a reply involves no tool call, so Stop and
_turn_currently_active()=False both fire the instant it's generated, well
before the user has had a chance to read it, let alone answer.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle

# _wait_for_turn_to_finish imports these lazily from their home modules
# on every call, so tests must patch the source, not the lifecycle module.
_FIND_ACTIVE_JSONL = "askr.session.monitor._find_active_jsonl"
_HAS_OUTSTANDING_SUBAGENT = "askr.session.checkpoint.has_outstanding_subagent"


class WaitForTurnToFinishTests(unittest.TestCase):
    def test_no_live_process_returns_false_immediately(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[]):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertFalse(result)

    def test_returns_once_stopped_no_new_turn_and_quiet_long_enough(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop", return_value=("2026-07-14T00:00:00+00:00", lifecycle.TURN_QUIET_GRACE_SECS)), \
             patch(_FIND_ACTIVE_JSONL, return_value="/some/project/transcript.jsonl"), \
             patch(_HAS_OUTSTANDING_SUBAGENT, return_value=False):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)

    def test_keeps_waiting_if_new_turn_started_before_it_noticed(self):
        # Simulates the exact bug: the original turn stopped, but a new one
        # started in the gap. Must NOT break on the first poll where
        # _turn_stopped_since is true if _turn_currently_active is also true.
        active_sequence = [True, True, False]  # new turn active for two polls, then quiet
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", side_effect=active_sequence) as mock_active, \
             patch.object(lifecycle, "_last_turn_stop", return_value=("2026-07-14T00:00:00+00:00", lifecycle.TURN_QUIET_GRACE_SECS)), \
             patch(_FIND_ACTIVE_JSONL, return_value="/some/project/transcript.jsonl"), \
             patch(_HAS_OUTSTANDING_SUBAGENT, return_value=False):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)
        self.assertEqual(mock_active.call_count, 3)  # kept polling through both "still active" reads

    def test_keeps_waiting_if_subagent_still_outstanding(self):
        # A dispatched Agent-tool subagent hasn't reported back — must not
        # open a companion just because the parent turn's Stop already fired.
        subagent_sequence = [True, True, False]
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop", return_value=("2026-07-14T00:00:00+00:00", lifecycle.TURN_QUIET_GRACE_SECS)), \
             patch(_FIND_ACTIVE_JSONL, return_value="/some/project/transcript.jsonl"), \
             patch(_HAS_OUTSTANDING_SUBAGENT, side_effect=subagent_sequence) as mock_subagent:
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)
        self.assertEqual(mock_subagent.call_count, 3)

    def test_keeps_waiting_until_quiet_grace_period_elapses(self):
        # The exact bug reported 2026-07-14: Claude ends a reply with a
        # plain-text question (no tool call) — Stop fires and
        # _turn_currently_active() goes False immediately, well before the
        # user has had any real chance to read it or respond. Must hold for
        # TURN_QUIET_GRACE_SECS of actual silence, not fire on the first poll.
        idle_sequence = [5, 30, lifecycle.TURN_QUIET_GRACE_SECS]  # seconds since Stop, growing each poll
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False), \
             patch.object(lifecycle, "_last_turn_stop",
                           side_effect=[("2026-07-14T00:00:00+00:00", s) for s in idle_sequence]) as mock_stop, \
             patch(_FIND_ACTIVE_JSONL, return_value="/some/project/transcript.jsonl"), \
             patch(_HAS_OUTSTANDING_SUBAGENT, return_value=False):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)
        self.assertEqual(mock_stop.call_count, 3)  # didn't break until the grace period was met

    def test_process_ending_mid_wait_breaks_loop(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", side_effect=[[123], []]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=False), \
             patch.object(lifecycle, "_turn_currently_active", return_value=True):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)

    def test_never_forces_through_a_genuinely_active_turn_past_max_wait(self):
        # 2026-08-10 fix (see the function's own MAX_WAIT_SECS comment):
        # the cap used to force an exit unconditionally at 600s, which fired
        # mid-reply during a single turn that legitimately ran past 10
        # minutes straight with zero Stop signals — confirmed in production.
        # The cap must now only ever short-circuit the UX-only grace period
        # once the turn itself has already finished; while turn_active stays
        # True, it has to keep polling PAST the 600s/POLL(5s)=120-poll mark,
        # not force-return early. This replaces a stale test asserting the
        # old (removed) forced-exit behavior — that version deadlocked the
        # whole suite: with time.sleep mocked to a no-op and turn_active
        # permanently True, the old assertion's scenario has no exit
        # condition left in the current implementation at all.
        active_sequence = [True] * 125 + [False]
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", side_effect=active_sequence) as mock_active, \
             patch.object(lifecycle, "_last_turn_stop", return_value=("2026-07-14T00:00:00+00:00", lifecycle.TURN_QUIET_GRACE_SECS)), \
             patch(_FIND_ACTIVE_JSONL, return_value="/some/project/transcript.jsonl"), \
             patch(_HAS_OUTSTANDING_SUBAGENT, return_value=False):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)
        # 126 calls: polled straight through the 120-poll (600s) mark until
        # turn_active finally went False — proof it didn't force an early exit.
        self.assertEqual(mock_active.call_count, 126)


if __name__ == "__main__":
    unittest.main()
