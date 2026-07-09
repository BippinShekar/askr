"""
Tests for askr/hooks/post_tool_use.py — Phase 3.13 S4 real-time user-rejection
detection (_REJECTION_RE, transcript tail reading, and _detect_and_save_rejection).

This is a fast, regex-only signal (not an LLM call) that fires on every tool
call, so it must stay cheap and conservative. Covers true/false-positive regex
cases, tool_result filtering, dedup across repeated calls in the same turn,
and end-to-end via main() stdin injection.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import post_tool_use


# ---------------------------------------------------------------------------
# _REJECTION_RE — true/false positive cases
# ---------------------------------------------------------------------------

class RejectionRegexTests(unittest.TestCase):
    def _matches(self, text):
        return bool(post_tool_use._REJECTION_RE.search(text))

    def test_no_thats_wrong_matches(self):
        self.assertTrue(self._matches("No, that's wrong, revert it."))

    def test_dont_do_that_matches(self):
        self.assertTrue(self._matches("Don't do that, use the other approach."))

    def test_thats_not_right_matches(self):
        self.assertTrue(self._matches("That's not right, try again."))

    def test_thats_not_correct_matches(self):
        self.assertTrue(self._matches("That's not correct."))

    def test_not_what_i_asked_matches(self):
        self.assertTrue(self._matches("That's not what I asked for."))

    def test_revert_that_matches(self):
        self.assertTrue(self._matches("Revert that change immediately."))

    def test_undo_that_matches(self):
        self.assertTrue(self._matches("Undo that."))

    def test_wrong_approach_matches(self):
        self.assertTrue(self._matches("This is the wrong approach entirely."))

    def test_case_insensitive(self):
        self.assertTrue(self._matches("NO, THAT'S WRONG."))

    def test_unrelated_sentence_does_not_match(self):
        self.assertFalse(self._matches("Let's add a new endpoint for the API."))

    def test_positive_feedback_does_not_match(self):
        self.assertFalse(self._matches("That's correct, ship it."))

    def test_neutral_question_does_not_match(self):
        self.assertFalse(self._matches("What approach should we use here?"))

    def test_vague_disagreement_does_not_match(self):
        # Under-capture is fine per roadmap.md's stated honest risk — this
        # regex is deliberately conservative, not exhaustive.
        self.assertFalse(self._matches("Hmm, I'm not totally sure about this."))


# ---------------------------------------------------------------------------
# _read_transcript_tail / _last_user_text_and_prior_assistant
# ---------------------------------------------------------------------------

class TranscriptTailTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.transcript_path = os.path.join(self._tmp.name, "transcript.jsonl")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_lines(self, entries):
        with open(self.transcript_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def test_missing_file_returns_empty(self):
        self.assertEqual(post_tool_use._read_transcript_tail("/nonexistent/path.jsonl"), [])

    def test_empty_path_returns_empty(self):
        self.assertEqual(post_tool_use._read_transcript_tail(""), [])

    def test_reads_all_entries_within_budget(self):
        self._write_lines([
            {"type": "user", "message": {"content": "hello"}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
        ])
        entries = post_tool_use._read_transcript_tail(self.transcript_path)
        self.assertEqual(len(entries), 2)

    def test_skips_malformed_lines(self):
        with open(self.transcript_path, "w") as f:
            f.write("not json\n")
            f.write(json.dumps({"type": "user", "message": {"content": "hi"}}) + "\n")
        entries = post_tool_use._read_transcript_tail(self.transcript_path)
        self.assertEqual(len(entries), 1)

    def test_tail_bytes_truncation_drops_only_earliest_entries(self):
        # Write many small entries, then read with a tiny tail_bytes budget —
        # the most recent entry must survive even though earlier ones don't.
        entries = [{"type": "user", "message": {"content": f"message number {i}"}} for i in range(200)]
        self._write_lines(entries)
        result = post_tool_use._read_transcript_tail(self.transcript_path, tail_bytes=200)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[-1]["message"]["content"], "message number 199")

    def test_last_user_text_skips_tool_result_entries(self):
        entries = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Editing the file now."}]}},
            {"type": "user", "message": {"content": "No, that's wrong, revert it."}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Edit"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
        ]
        last_user, prior_assistant = post_tool_use._last_user_text_and_prior_assistant(entries)
        self.assertEqual(last_user, "No, that's wrong, revert it.")

    def test_prior_assistant_text_captured(self):
        entries = [
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll rewrite the auth flow to use JWTs."}]}},
            {"type": "user", "message": {"content": "No, that's wrong, we use sessions."}},
        ]
        last_user, prior_assistant = post_tool_use._last_user_text_and_prior_assistant(entries)
        self.assertEqual(last_user, "No, that's wrong, we use sessions.")
        self.assertIn("JWTs", prior_assistant)

    def test_no_user_entries_returns_empty_strings(self):
        entries = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}}]
        last_user, prior_assistant = post_tool_use._last_user_text_and_prior_assistant(entries)
        self.assertEqual(last_user, "")
        self.assertEqual(prior_assistant, "")


# ---------------------------------------------------------------------------
# _detect_and_save_rejection
# ---------------------------------------------------------------------------

class DetectAndSaveRejectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.transcript_path = os.path.join(self._tmp.name, "transcript.jsonl")

    def tearDown(self):
        self._tmp.cleanup()

    def _write_transcript(self, entries):
        with open(self.transcript_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def _rejections(self):
        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        if not os.path.exists(path):
            return []
        with open(path) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_high_confidence_rejection_is_written(self):
        self._write_transcript([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll add a global mutex around all writes."}]}},
            {"type": "user", "message": {"content": "No, that's wrong, don't do that."}},
        ])
        post_tool_use._detect_and_save_rejection(self.transcript_path, self.state_dir, "askr/state/writer.py", "alice")

        rejections = self._rejections()
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]["dev"], "alice")
        self.assertEqual(rejections[0]["domain"], "askr/state/writer.py")
        self.assertEqual(rejections[0]["source"], "realtime_regex")
        self.assertIn("global mutex", rejections[0]["what_was_proposed"])

    def test_no_match_writes_nothing(self):
        self._write_transcript([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Adding the new endpoint."}]}},
            {"type": "user", "message": {"content": "Looks good, thanks."}},
        ])
        post_tool_use._detect_and_save_rejection(self.transcript_path, self.state_dir, "api.py", "alice")
        self.assertEqual(self._rejections(), [])

    def test_dedup_across_repeated_calls_same_turn(self):
        self._write_transcript([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Using a global mutex."}]}},
            {"type": "user", "message": {"content": "No, that's wrong, don't do that."}},
        ])
        post_tool_use._detect_and_save_rejection(self.transcript_path, self.state_dir, "a.py", "alice")
        post_tool_use._detect_and_save_rejection(self.transcript_path, self.state_dir, "a.py", "alice")
        self.assertEqual(len(self._rejections()), 1)

    def test_missing_transcript_is_noop(self):
        post_tool_use._detect_and_save_rejection("/nonexistent.jsonl", self.state_dir, "a.py", "alice")
        self.assertEqual(self._rejections(), [])

    def test_no_file_path_uses_unknown_domain(self):
        self._write_transcript([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Doing X."}]}},
            {"type": "user", "message": {"content": "That's not right, please don't use that."}},
        ])
        post_tool_use._detect_and_save_rejection(self.transcript_path, self.state_dir, "", "alice")
        rejections = self._rejections()
        self.assertEqual(len(rejections), 1)
        self.assertEqual(rejections[0]["domain"], "unknown")


# ---------------------------------------------------------------------------
# main() end-to-end
# ---------------------------------------------------------------------------

class MainEndToEndRejectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self.state_dir = os.path.join(self.project_dir, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.transcript_path = os.path.join(self.project_dir, "transcript.jsonl")

        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)
        self._orig_stdin = sys.stdin

    def tearDown(self):
        sys.stdin = self._orig_stdin
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _write_transcript(self, entries):
        with open(self.transcript_path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def _feed(self, payload):
        sys.stdin = __import__("io").StringIO(json.dumps(payload))

    def test_main_writes_rejection_from_stdin_payload(self):
        self._write_transcript([
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "I'll hardcode the API key."}]}},
            {"type": "user", "message": {"content": "No, that's wrong, don't do that."}},
        ])
        target = os.path.join(self.project_dir, "config.py")
        with open(target, "w") as f:
            f.write("x = 1\n")

        self._feed({
            "tool_name": "Edit",
            "tool_input": {"file_path": target, "old_string": "x = 1", "new_string": "x = 2"},
            "session_id": "sess-1",
            "transcript_path": self.transcript_path,
        })

        with patch("askr.session.monitor.get_session_stats", return_value=None):
            post_tool_use.main()

        path = os.path.join(self.state_dir, "rejected_decisions.jsonl")
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            entries = [json.loads(l) for l in f if l.strip()]
        self.assertEqual(len(entries), 1)
        self.assertIn("hardcode the API key", entries[0]["what_was_proposed"])


if __name__ == "__main__":
    unittest.main()
