"""
Tests for askr/state/goals.py — previously had zero coverage.

Covers the state_dir-threaded API (used by the multi-project daemon path
in checkpoint.py/lifecycle.py) as well as the legacy ambient-cwd path (used
by the CLI).
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import goals


class GoalsStateDirTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_and_load_today_goal(self):
        goals._append({
            "id": "abc123", "text": "ship the thing", "status": "open",
            "date": goals._today(), "added": goals._now_iso(),
            "auto_suggested": False, "done_at": None,
        }, self.state_dir)

        self.assertEqual(goals.load_today_goals(self.state_dir), ["ship the thing"])
        self.assertEqual(goals.load_open_goals(self.state_dir), ["ship the thing"])

    def test_complete_goal_marks_done_and_drops_from_open(self):
        goals._append({
            "id": "abc123", "text": "ship the thing", "status": "open",
            "date": goals._today(), "added": goals._now_iso(),
            "auto_suggested": False, "done_at": None,
        }, self.state_dir)

        self.assertTrue(goals.complete_goal("ship the thing", self.state_dir))
        self.assertEqual(goals.load_open_goals(self.state_dir), [])

    def test_complete_goal_returns_false_when_not_found(self):
        self.assertFalse(goals.complete_goal("does not exist", self.state_dir))

    def test_last_entry_per_id_wins(self):
        """_read_all uses last-entry-per-id — append-only update pattern."""
        entry = {
            "id": "abc123", "text": "ship the thing", "status": "open",
            "date": goals._today(), "added": goals._now_iso(),
            "auto_suggested": False, "done_at": None,
        }
        goals._append(entry, self.state_dir)
        goals._append({**entry, "status": "done", "done_at": goals._now_iso()}, self.state_dir)

        all_goals = goals._read_all(self.state_dir)
        self.assertEqual(len(all_goals), 1)
        self.assertEqual(all_goals[0]["status"], "done")

    def test_expire_auto_suggested_goals_only_touches_auto_suggested(self):
        goals._append({
            "id": "auto1", "text": "auto goal", "status": "open",
            "date": goals._today(), "added": goals._now_iso(),
            "auto_suggested": True, "done_at": None,
        }, self.state_dir)
        goals._append({
            "id": "manual1", "text": "manual goal", "status": "open",
            "date": goals._today(), "added": goals._now_iso(),
            "auto_suggested": False, "done_at": None,
        }, self.state_dir)

        count = goals.expire_auto_suggested_goals(self.state_dir)

        self.assertEqual(count, 1)
        open_texts = goals.load_open_goals(self.state_dir)
        self.assertEqual(open_texts, ["manual goal"])

    def test_read_all_skips_malformed_lines_without_raising(self):
        path = goals._path(self.state_dir)
        os.makedirs(self.state_dir, exist_ok=True)
        with open(path, "w") as f:
            f.write("not json\n")
            f.write('{"id": "ok1", "text": "valid", "status": "open"}\n')

        result = goals._read_all(self.state_dir)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "valid")

    def test_state_dir_isolation_two_projects_do_not_collide(self):
        with tempfile.TemporaryDirectory() as other_dir:
            goals._append({
                "id": "a", "text": "project A goal", "status": "open",
                "date": goals._today(), "added": goals._now_iso(),
                "auto_suggested": False, "done_at": None,
            }, self.state_dir)
            goals._append({
                "id": "b", "text": "project B goal", "status": "open",
                "date": goals._today(), "added": goals._now_iso(),
                "auto_suggested": False, "done_at": None,
            }, other_dir)

            self.assertEqual(goals.load_open_goals(self.state_dir), ["project A goal"])
            self.assertEqual(goals.load_open_goals(other_dir), ["project B goal"])


class LoadDoneTodayTimezoneTests(unittest.TestCase):
    """load_done_today() compares done_at (stored in UTC) against the local
    calendar date. A naive iso_utc[:10] string-slice comparison silently drops
    (or wrongly includes) goals completed near local midnight whenever the
    local UTC offset is nonzero — _to_local_date() must actually convert."""

    def test_to_local_date_converts_via_astimezone_not_string_slice(self):
        with patch("askr.state.goals.datetime") as mock_dt:
            mock_dt.fromisoformat.return_value.astimezone.return_value.strftime.return_value = "2026-07-02"
            result = goals._to_local_date("2026-07-03T02:00:00Z")

        self.assertEqual(result, "2026-07-02")
        mock_dt.fromisoformat.assert_called_once_with("2026-07-03T02:00:00+00:00")

    def test_to_local_date_falls_back_to_slice_on_bad_input(self):
        self.assertEqual(goals._to_local_date("not-a-timestamp"), "not-a-time")
        self.assertEqual(goals._to_local_date(""), "")

    def test_load_done_today_includes_goal_completed_today(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(os, "getcwd", return_value=tmp):
            os.makedirs(os.path.join(tmp, "askr_state"), exist_ok=True)
            goals._append({
                "id": "abc123", "text": "shipped it", "status": "done",
                "date": goals._today(), "added": goals._now_iso(),
                "auto_suggested": False, "done_at": goals._now_iso(),
            })
            self.assertEqual(goals.load_done_today(), ["shipped it"])


if __name__ == "__main__":
    unittest.main()
