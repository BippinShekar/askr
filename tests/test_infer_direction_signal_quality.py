"""
Regression coverage for two 2026-07-09 fixes to _infer_direction's signal
quality, found while diagnosing a user report of "confidence only 50%"
firing right after a session that clearly concluded with a real direction:

1. Signal 4 (commit-scope/file-path clustering) used to sample the raw last
   10 commits, including askr's own automated "askr: checkpoint"/"askr: idle"
   commits — which never contribute a scope or path signal (their messages
   don't match the conventional-commit regex, their files are always under
   askr_state/), so an idle-heavy stretch diluted the window down to just a
   handful of real commits, weakening confidence for no real reason.

2. Signal 3 (handover next_actions) used to accept the degraded fallback
   handover's generic "review manually" text as a confident (0.85) direction,
   since it's >=10 chars — masking a failed handover generation as if it
   were a real next step instead of falling through to weaker signals.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.lifecycle import _infer_direction


def _run_git(args, cwd):
    subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, check=True)


def _init_repo(tmpdir):
    _run_git(["init", "-q"], tmpdir)
    _run_git(["config", "user.email", "test@test.com"], tmpdir)
    _run_git(["config", "user.name", "Test"], tmpdir)
    os.makedirs(os.path.join(tmpdir, "askr_state"), exist_ok=True)


def _commit(tmpdir, message):
    _run_git(["commit", "--allow-empty", "-m", message], tmpdir)


class Signal4ExcludesAutomatedCommitsTests(unittest.TestCase):
    def test_askr_automated_commits_do_not_dilute_the_window(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            # No uncommitted files, no blockers, no handover history — force
            # the walk down to Signal 4.
            _commit(tmpdir, "fix(voice): serialize output")
            for i in range(8):
                _commit(tmpdir, f"askr: idle [dev] 2026-07-09 12:{i:02d}")
            _commit(tmpdir, "fix(voice): another real fix")

            result = _infer_direction(tmpdir)
            # Both real commits share the "voice" scope — without the
            # automated-commit exclusion, only 2 of the last 10 raw commits
            # would even be real, but the exclusion means git itself walks
            # past the "askr: idle" noise, so the scope signal is still
            # found cleanly.
            self.assertEqual(result["signal_source"], "commit_scope")
            self.assertIn("voice", result["direction"])

    def test_pure_automated_history_falls_through_to_no_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            for i in range(10):
                _commit(tmpdir, f"askr: idle [dev] 2026-07-09 12:{i:02d}")

            result = _infer_direction(tmpdir)
            self.assertEqual(result["signal_source"], "none")
            self.assertEqual(result["confidence"], 0.35)


def _commit_handover(tmpdir, message, next_actions):
    """Write handover_dev.json with the given next_actions and commit it."""
    handover = {"task": "test", "next_actions": next_actions, "files_in_play": []}
    with open(os.path.join(tmpdir, "askr_state", "handover_dev.json"), "w") as f:
        json.dump(handover, f)
    _run_git(["add", "askr_state/handover_dev.json"], tmpdir)
    _run_git(["commit", "-m", message], tmpdir)


class Signal3SkipsFallbackPlaceholderTests(unittest.TestCase):
    def test_fallback_placeholder_is_skipped_for_an_older_real_direction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            with patch("askr.state.config.load_developer", return_value="dev"):
                # Oldest: just an anchor commit so the middle one has a diff pair.
                _commit_handover(tmpdir, "askr: checkpoint [dev] oldest", [])
                # Middle: a REAL direction.
                _commit_handover(tmpdir, "askr: checkpoint [dev] middle", [
                    {"order": 1, "action": "implement the OAuth flow from research", "why": "discussed and agreed"},
                ])
                # Newest: degraded fallback placeholder — must be skipped, not
                # returned as a confident 0.85 direction.
                _commit_handover(tmpdir, "askr: checkpoint [dev] newest", [
                    {"order": 1, "action": "Inspect foo.py — verify manually", "why": "handover generation failed this session"},
                ])

                result = _infer_direction(tmpdir)
                self.assertEqual(result["signal_source"], "handover_next_actions")
                self.assertIn("OAuth", result["direction"])

    def test_real_action_with_different_why_is_not_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            with patch("askr.state.config.load_developer", return_value="dev"):
                _commit_handover(tmpdir, "askr: checkpoint [dev] oldest", [])
                _commit_handover(tmpdir, "askr: checkpoint [dev] newest", [
                    {"order": 1, "action": "implement the OAuth flow from research", "why": "discussed and agreed"},
                ])

                result = _infer_direction(tmpdir)
                self.assertEqual(result["signal_source"], "handover_next_actions")
                self.assertIn("OAuth", result["direction"])


if __name__ == "__main__":
    unittest.main()
