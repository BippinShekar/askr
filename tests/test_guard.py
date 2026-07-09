"""
Tests for askr/session/guard.py — the implementation guard's context assembly
and Haiku cross-check (Phase 3.13 S3: user-rejected decisions).

Covers _load_rejected_decisions (domain/file_path substring matching) and its
wiring into _load_context / run_guard_check's prompt. call_claude is always
mocked — no real network calls.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import guard


class LoadRejectedDecisionsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, entries):
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        with open(path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_missing_file_returns_empty(self):
        self.assertEqual(guard._load_rejected_decisions(self.state_dir, "askr/session/guard.py"), "")

    def test_domain_matching_file_path_is_included(self):
        self._write([{
            "at": "2026-07-09 10:00", "dev": "bippin",
            "what_was_proposed": "use a single global lock for all file writes",
            "user_signal": "no, that will serialize unrelated developers",
            "domain": "askr/state/writer.py",
            "confidence": 0.9,
        }])
        result = guard._load_rejected_decisions(self.state_dir, "/repo/askr/state/writer.py")
        self.assertIn("use a single global lock", result)
        self.assertIn("askr/state/writer.py", result)

    def test_domain_not_matching_file_path_is_excluded(self):
        self._write([{
            "at": "2026-07-09 10:00", "dev": "bippin",
            "what_was_proposed": "rewrite the CLI in Rust",
            "user_signal": "no, keep it Python",
            "domain": "askr/cli/askr.py",
            "confidence": 0.9,
        }])
        result = guard._load_rejected_decisions(self.state_dir, "/repo/askr/session/guard.py")
        self.assertEqual(result, "")

    def test_no_file_path_includes_all_entries_with_a_domain(self):
        self._write([
            {"what_was_proposed": "proposal one", "user_signal": "no", "domain": "a.py", "confidence": 0.8},
            {"what_was_proposed": "proposal two", "user_signal": "no", "domain": "b.py", "confidence": 0.8},
        ])
        result = guard._load_rejected_decisions(self.state_dir, "")
        self.assertIn("proposal one", result)
        self.assertIn("proposal two", result)

    def test_entry_with_empty_domain_excluded_when_file_path_given(self):
        self._write([{
            "what_was_proposed": "some vague proposal",
            "user_signal": "no",
            "domain": "",
            "confidence": 0.8,
        }])
        result = guard._load_rejected_decisions(self.state_dir, "/repo/some/file.py")
        self.assertEqual(result, "")

    def test_limit_lines_caps_output_to_most_recent(self):
        self._write([
            {"what_was_proposed": f"proposal {i}", "user_signal": "no", "domain": "x.py", "confidence": 0.8}
            for i in range(5)
        ])
        result = guard._load_rejected_decisions(self.state_dir, "x.py", limit_lines=2)
        self.assertNotIn("proposal 0", result)
        self.assertIn("proposal 3", result)
        self.assertIn("proposal 4", result)

    def test_malformed_line_is_skipped_not_fatal(self):
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        with open(path, "w") as f:
            f.write("not json\n")
            f.write(json.dumps({
                "what_was_proposed": "valid proposal", "user_signal": "no",
                "domain": "x.py", "confidence": 0.8,
            }) + "\n")
        result = guard._load_rejected_decisions(self.state_dir, "x.py")
        self.assertIn("valid proposal", result)


class LoadContextIncludesRejectedDecisionsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_context_dict_has_rejected_decisions_key(self):
        context = guard._load_context("bippin", self.state_dir, "some/file.py")
        self.assertIn("rejected_decisions", context)

    def test_rejected_decisions_alone_prevents_no_context_shortcut(self):
        # Only rejected_decisions.jsonl populated, everything else empty —
        # run_guard_check must still proceed to the LLM call rather than
        # short-circuiting via the "no architecture context available" path.
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        with open(path, "w") as f:
            f.write(json.dumps({
                "what_was_proposed": "use approach X", "user_signal": "no",
                "domain": "target.py", "confidence": 0.9,
            }) + "\n")

        with patch("askr.clients.claude.call_claude") as mock_call:
            mock_call.return_value = json.dumps({"clean": True, "issues": [], "summary": "ok"})
            result = guard.run_guard_check(
                {"reason": "new_file", "tool": "Write", "file_path": "target.py"},
                "bippin", self.state_dir,
            )
        mock_call.assert_called_once()
        prompt = mock_call.call_args[0][1]
        self.assertIn("use approach X", prompt)
        self.assertIn("USER-REJECTED DECISIONS", prompt)
        self.assertTrue(result["clean"])


if __name__ == "__main__":
    unittest.main()
