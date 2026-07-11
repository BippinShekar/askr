"""
Tests for lifecycle._wait_for_turn_to_finish's 2026-07-11 fix: a companion
session (or quota checkpoint) must not open the instant the ONE turn that
was active when the trigger fired ends — if the user immediately started a
new turn in that gap, opening then looks and feels identical to being
interrupted mid-reply. The wait must hold until there's a genuinely quiet
moment: the triggering turn stopped AND no new turn is currently active.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class WaitForTurnToFinishTests(unittest.TestCase):
    def test_no_live_process_returns_false_immediately(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[]):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertFalse(result)

    def test_returns_once_stopped_and_no_new_turn_active(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=False):
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
             patch.object(lifecycle, "_turn_currently_active", side_effect=active_sequence) as mock_active:
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)
        self.assertEqual(mock_active.call_count, 3)  # kept polling through both "still active" reads

    def test_process_ending_mid_wait_breaks_loop(self):
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", side_effect=[[123], []]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=False), \
             patch.object(lifecycle, "_turn_currently_active", return_value=True):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)

    def test_max_wait_cap_still_applies_if_never_quiet(self):
        # Every poll: stopped but a turn is always active (rapid chat, never
        # a gap). Must still give up after MAX_WAIT_SECS, not loop forever.
        with patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[123]), \
             patch.object(lifecycle.time, "sleep"), \
             patch.object(lifecycle, "_turn_stopped_since", return_value=True), \
             patch.object(lifecycle, "_turn_currently_active", return_value=True):
            result = lifecycle._wait_for_turn_to_finish("/some/project", "sess-1")
        self.assertTrue(result)  # gives up and proceeds anyway after the cap


if __name__ == "__main__":
    unittest.main()
