"""
Tests for the blockers fix: per-dev handover_<dev>.json blockers[] aggregation
replacing the dead, racy shared blockers.md as the automated signal source.

See askr/state/reader.py:load_blockers() and
askr/session/lifecycle.py:_infer_direction() Signal 2.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import reader
from askr.session import lifecycle


def _write_handover(state_dir, dev, blockers=None):
    with open(os.path.join(state_dir, f"handover_{dev}.json"), "w") as f:
        json.dump({"blockers": blockers or []}, f)


class LoadBlockersTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name
        self._patch = patch("askr.state.reader.state_path",
                             side_effect=lambda name: os.path.join(self.state_dir, name))
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_no_handovers_no_blockers_md_returns_empty(self):
        self.assertEqual(reader.load_blockers("alice"), "")

    def test_aggregates_blockers_from_multiple_devs(self):
        _write_handover(self.state_dir, "alice", ["API rate limit on staging"])
        _write_handover(self.state_dir, "bob", ["waiting on design review"])

        result = reader.load_blockers("alice")

        self.assertIn("(you) API rate limit on staging", result)
        self.assertIn("(bob) waiting on design review", result)

    def test_dev_with_no_blockers_is_skipped(self):
        _write_handover(self.state_dir, "alice", [])
        _write_handover(self.state_dir, "bob", ["real blocker"])

        result = reader.load_blockers("alice")

        self.assertNotIn("(you)", result)
        self.assertIn("(bob) real blocker", result)

    def test_malformed_handover_json_does_not_raise(self):
        with open(os.path.join(self.state_dir, "handover_alice.json"), "w") as f:
            f.write("not valid json")

        result = reader.load_blockers("alice")
        self.assertEqual(result, "")

    def test_manual_blockers_md_appended(self):
        with open(os.path.join(self.state_dir, "blockers.md"), "w") as f:
            f.write("# Blockers\n\n## Known Bugs\n- legacy manual note\n")

        result = reader.load_blockers("alice")
        self.assertIn("legacy manual note", result)


class InferDirectionBlockersSignalTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_path = self._tmp.name
        os.makedirs(os.path.join(self.project_path, "askr_state"))

    def tearDown(self):
        self._tmp.cleanup()

    @patch("askr.session.lifecycle.subprocess.run")
    def test_blocker_in_handover_json_triggers_signal(self, mock_run):
        mock_run.return_value.stdout = ""  # no uncommitted files (Signal 1 stays quiet)
        _write_handover(os.path.join(self.project_path, "askr_state"), "alice",
                         ["blocked on third-party API key"])

        result = lifecycle._infer_direction(self.project_path)

        self.assertEqual(result["signal_source"], "blockers")
        self.assertIn("blocked on third-party API key", result["direction"])

    @patch("askr.session.lifecycle.subprocess.run")
    def test_no_blockers_anywhere_falls_through(self, mock_run):
        mock_run.return_value.stdout = ""
        _write_handover(os.path.join(self.project_path, "askr_state"), "alice", [])

        result = lifecycle._infer_direction(self.project_path)

        self.assertNotEqual(result.get("signal_source"), "blockers")


if __name__ == "__main__":
    unittest.main()
