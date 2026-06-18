"""
Tests for the merge-not-replace state writers in checkpoint.py.

These accumulate across sessions (decisions.jsonl, failed_approaches.md) and
must never lose prior entries or duplicate ones already recorded — both are
explicit rules in the handover prompt (checkpoint.py) but were previously
unverified by any test.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.checkpoint import _append_failed_approaches, _write_decisions_from_handover


class AppendFailedApproachesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _read(self):
        path = os.path.join(self.state_dir, "failed_approaches.md")
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()

    def test_appends_new_entry(self):
        handover = {"failed_approaches": [{"approach": "tried mocking the database", "reason": "masked a real migration bug"}]}
        _append_failed_approaches(handover, self.state_dir)

        content = self._read()
        self.assertIn("tried mocking the database", content)
        self.assertIn("masked a real migration bug", content)

    def test_does_not_duplicate_existing_entry(self):
        handover = {"failed_approaches": [{"approach": "tried mocking the database", "reason": "masked a real bug"}]}
        _append_failed_approaches(handover, self.state_dir)
        first = self._read()

        _append_failed_approaches(handover, self.state_dir)
        second = self._read()

        self.assertEqual(first, second)
        self.assertEqual(second.count("tried mocking the database"), 1)

    def test_short_entries_filtered_out(self):
        handover = {"failed_approaches": [{"approach": "no", "reason": ""}]}
        _append_failed_approaches(handover, self.state_dir)
        self.assertEqual(self._read(), "")

    def test_none_handover_is_noop(self):
        _append_failed_approaches(None, self.state_dir)
        self.assertEqual(self._read(), "")


class WriteDecisionsFromHandoverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _read_lines(self):
        path = os.path.join(self.state_dir, "decisions.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_appends_new_decision(self):
        handover = {"decisions": [{"decision": "Use per-dev blockers JSON instead of shared file", "reason": "avoids write races"}]}
        _write_decisions_from_handover(handover, self.state_dir, "alice")

        lines = self._read_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["dev"], "alice")
        self.assertEqual(lines[0]["decision"], "Use per-dev blockers JSON instead of shared file")

    def test_does_not_duplicate_existing_decision(self):
        handover = {"decisions": [{"decision": "Use per-dev blockers JSON instead of shared file", "reason": "avoids write races"}]}
        _write_decisions_from_handover(handover, self.state_dir, "alice")
        _write_decisions_from_handover(handover, self.state_dir, "alice")

        self.assertEqual(len(self._read_lines()), 1)

    def test_non_dict_handover_is_noop(self):
        _write_decisions_from_handover("legacy markdown string", self.state_dir, "alice")
        self.assertEqual(self._read_lines(), [])

    def test_existing_decisions_from_other_devs_preserved(self):
        with open(os.path.join(self.state_dir, "decisions.jsonl"), "w") as f:
            f.write(json.dumps({"at": "2026-01-01 00:00", "dev": "bob", "decision": "older decision", "reason": ""}) + "\n")

        handover = {"decisions": [{"decision": "new decision from alice", "reason": ""}]}
        _write_decisions_from_handover(handover, self.state_dir, "alice")

        lines = self._read_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual({l["decision"] for l in lines}, {"older decision", "new decision from alice"})


if __name__ == "__main__":
    unittest.main()
