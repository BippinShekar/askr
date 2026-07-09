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

from askr.session.checkpoint import (
    _append_failed_approaches,
    _write_decisions_from_handover,
    _write_rejections_from_handover,
    _build_fallback_handover_dict,
    _tail_decisions_jsonl,
    _tail_failed_approaches,
    _tail_rejected_decisions_jsonl,
)


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


class WriteRejectionsFromHandoverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _read_lines(self):
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_appends_new_rejection(self):
        handover = {"user_rejected_decisions": [{
            "what_was_proposed": "Use a shared global lock for all writes",
            "user_signal": "no, that will deadlock under concurrent sessions",
            "domain": "askr/state/writer.py",
            "confidence": 0.9,
        }]}
        _write_rejections_from_handover(handover, self.state_dir, "alice")

        lines = self._read_lines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["dev"], "alice")
        self.assertEqual(lines[0]["what_was_proposed"], "Use a shared global lock for all writes")
        self.assertEqual(lines[0]["domain"], "askr/state/writer.py")
        self.assertEqual(lines[0]["confidence"], 0.9)
        self.assertEqual(lines[0]["source"], "checkpoint")

    def test_does_not_duplicate_existing_rejection(self):
        handover = {"user_rejected_decisions": [{
            "what_was_proposed": "Use a shared global lock for all writes",
            "user_signal": "no, that will deadlock",
            "domain": "writer.py",
            "confidence": 0.9,
        }]}
        _write_rejections_from_handover(handover, self.state_dir, "alice")
        _write_rejections_from_handover(handover, self.state_dir, "alice")

        self.assertEqual(len(self._read_lines()), 1)

    def test_below_confidence_threshold_is_skipped(self):
        handover = {"user_rejected_decisions": [{
            "what_was_proposed": "Rewrite the guard in Rust",
            "user_signal": "hmm, maybe not",
            "domain": "guard.py",
            "confidence": 0.4,
        }]}
        _write_rejections_from_handover(handover, self.state_dir, "alice")
        self.assertEqual(self._read_lines(), [])

    def test_short_proposed_text_filtered_out(self):
        handover = {"user_rejected_decisions": [{
            "what_was_proposed": "no",
            "user_signal": "no",
            "domain": "x.py",
            "confidence": 0.9,
        }]}
        _write_rejections_from_handover(handover, self.state_dir, "alice")
        self.assertEqual(self._read_lines(), [])

    def test_non_dict_handover_is_noop(self):
        _write_rejections_from_handover("legacy markdown string", self.state_dir, "alice")
        self.assertEqual(self._read_lines(), [])

    def test_none_handover_is_noop(self):
        _write_rejections_from_handover(None, self.state_dir, "alice")
        self.assertEqual(self._read_lines(), [])

    def test_existing_rejections_from_other_devs_preserved(self):
        with open(os.path.join(self.state_dir, "rejected_decisions.jsonl"), "w") as f:
            f.write(json.dumps({
                "at": "2026-01-01 00:00", "dev": "bob",
                "what_was_proposed": "older proposal that was rejected",
                "user_signal": "no", "domain": "old.py", "confidence": 0.9,
            }) + "\n")

        handover = {"user_rejected_decisions": [{
            "what_was_proposed": "new proposal from alice's session",
            "user_signal": "not what I wanted",
            "domain": "new.py",
            "confidence": 0.9,
        }]}
        _write_rejections_from_handover(handover, self.state_dir, "alice")

        lines = self._read_lines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(
            {l["what_was_proposed"] for l in lines},
            {"older proposal that was rejected", "new proposal from alice's session"},
        )


class FallbackHandoverSelfHealingTests(unittest.TestCase):
    """
    A degraded (LLM-failed) checkpoint used to copy decisions/failed_approaches
    straight from existing_handover. Once one failed run gutted that dict to [],
    every subsequent failed run copied the emptiness forward forever — even
    though decisions.jsonl and failed_approaches.md (append-only, never gutted)
    still had the real history. The fallback must re-derive from those files
    instead of trusting existing_handover's arrays.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write_decisions(self, decisions):
        path = os.path.join(self.state_dir, "decisions.jsonl")
        with open(path, "w") as f:
            for d in decisions:
                f.write(json.dumps(d) + "\n")

    def _write_failed_approaches(self, bullets):
        path = os.path.join(self.state_dir, "failed_approaches.md")
        with open(path, "w") as f:
            f.write("# Failed Approaches\n\n")
            for b in bullets:
                f.write(f"- {b}\n")

    def _write_rejected_decisions(self, rejections):
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        with open(path, "w") as f:
            for r in rejections:
                f.write(json.dumps(r) + "\n")

    def test_recovers_decisions_when_existing_handover_is_gutted(self):
        self._write_decisions([
            {"at": "2026-07-01 00:00", "dev": "bippin", "decision": "use Zarvox as default voice", "reason": "Samantha sounds like Siri"},
        ])
        existing_handover = {"decisions": [], "failed_approaches": [], "files_in_play": []}

        result = _build_fallback_handover_dict([], existing_handover, "stop", state_dir=self.state_dir)

        self.assertEqual(len(result["decisions"]), 1)
        self.assertEqual(result["decisions"][0]["decision"], "use Zarvox as default voice")

    def test_recovers_failed_approaches_when_existing_handover_is_gutted(self):
        self._write_failed_approaches(["mocking the database — masked a real migration bug"])
        existing_handover = {"decisions": [], "failed_approaches": [], "files_in_play": []}

        result = _build_fallback_handover_dict([], existing_handover, "stop", state_dir=self.state_dir)

        self.assertEqual(len(result["failed_approaches"]), 1)
        self.assertIn("mocking the database", result["failed_approaches"][0]["approach"])

    def test_no_state_dir_falls_back_to_existing_handover(self):
        existing_handover = {"decisions": [{"decision": "kept as-is", "reason": ""}], "failed_approaches": [], "files_in_play": []}

        result = _build_fallback_handover_dict([], existing_handover, "stop")

        self.assertEqual(result["decisions"], [{"decision": "kept as-is", "reason": ""}])

    def test_recovers_rejected_decisions_when_existing_handover_is_gutted(self):
        self._write_rejected_decisions([{
            "at": "2026-07-01 00:00", "dev": "bippin",
            "what_was_proposed": "switch to a single global decisions file",
            "user_signal": "no, keep it per-dev",
            "domain": "askr_state/decisions.jsonl",
            "confidence": 0.85,
        }])
        existing_handover = {"decisions": [], "failed_approaches": [], "user_rejected_decisions": [], "files_in_play": []}

        result = _build_fallback_handover_dict([], existing_handover, "stop", state_dir=self.state_dir)

        self.assertEqual(len(result["user_rejected_decisions"]), 1)
        self.assertEqual(
            result["user_rejected_decisions"][0]["what_was_proposed"],
            "switch to a single global decisions file",
        )

    def test_tail_decisions_jsonl_returns_last_n(self):
        self._write_decisions([{"decision": f"decision {i}", "reason": ""} for i in range(10)])
        result = _tail_decisions_jsonl(self.state_dir, n=3)
        self.assertEqual([d["decision"] for d in result], ["decision 7", "decision 8", "decision 9"])

    def test_tail_decisions_jsonl_missing_file_returns_empty(self):
        self.assertEqual(_tail_decisions_jsonl(self.state_dir), [])

    def test_tail_failed_approaches_missing_file_returns_empty(self):
        self.assertEqual(_tail_failed_approaches(self.state_dir), [])

    def test_tail_rejected_decisions_jsonl_returns_last_n(self):
        self._write_rejected_decisions([
            {"what_was_proposed": f"proposal {i}", "user_signal": "no", "domain": "x.py", "confidence": 0.8}
            for i in range(10)
        ])
        result = _tail_rejected_decisions_jsonl(self.state_dir, n=3)
        self.assertEqual(
            [d["what_was_proposed"] for d in result],
            ["proposal 7", "proposal 8", "proposal 9"],
        )

    def test_tail_rejected_decisions_jsonl_missing_file_returns_empty(self):
        self.assertEqual(_tail_rejected_decisions_jsonl(self.state_dir), [])


if __name__ == "__main__":
    unittest.main()
