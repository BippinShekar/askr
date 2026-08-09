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

from askr.session import lifecycle
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


class Signal3StalenessCrossCheckTests(unittest.TestCase):
    """
    2026-08-09: a session can finish real work (commit it) and end without
    ever crossing a real trigger threshold (context/quota/idle) — its own
    checkpoint never fires, so canonical handover_dev.json stays exactly as
    the PREVIOUS session left it, still listing the now-resolved next_action.
    A fresh autonomous launch trusting that blind burns real tokens
    re-verifying work someone already finished (confirmed live: a session
    spent several tool calls and ~3.5 minutes confirming two already-fixed
    issues before finding anything new to do).
    """

    def test_real_commit_after_handover_drops_the_stale_direction(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            with patch("askr.state.config.load_developer", return_value="dev"):
                _commit_handover(tmpdir, "askr: checkpoint [dev] oldest", [])
                _commit_handover(tmpdir, "askr: checkpoint [dev] newest", [
                    {"order": 1, "action": "implement the OAuth flow from research", "why": "discussed and agreed"},
                ])
                # A later session did the work and committed it directly,
                # without ever triggering its own checkpoint.
                _commit(tmpdir, "fix(auth): implement OAuth flow")

                result = _infer_direction(tmpdir)
                self.assertNotEqual(result["signal_source"], "handover_next_actions")
                self.assertNotIn("OAuth", result["direction"])

    def test_no_commits_after_handover_still_returns_the_direction(self):
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

    def test_only_askr_automated_commits_after_handover_do_not_count_as_stale(self):
        # Routine checkpoint/idle housekeeping commits happen regardless of
        # whether the next_action was resolved — they must not themselves
        # invalidate an otherwise still-valid direction.
        with tempfile.TemporaryDirectory() as tmpdir:
            _init_repo(tmpdir)
            with patch("askr.state.config.load_developer", return_value="dev"):
                _commit_handover(tmpdir, "askr: checkpoint [dev] oldest", [])
                _commit_handover(tmpdir, "askr: checkpoint [dev] newest", [
                    {"order": 1, "action": "implement the OAuth flow from research", "why": "discussed and agreed"},
                ])
                _commit(tmpdir, "askr: idle [dev] 2026-08-09 09:00")

                result = _infer_direction(tmpdir)
                self.assertEqual(result["signal_source"], "handover_next_actions")
                self.assertIn("OAuth", result["direction"])


class StartClaudeUsesInferDirectionTests(unittest.TestCase):
    """
    2026-08-09: _start_claude() — used by the idle/goal autolaunch path and
    the quota trigger's post-reset relaunch — was the only one of the three
    launch paths that never called _infer_direction() at all, just
    unconditionally "read the handover, execute the Next Action, priority
    over everything else." The other two (_open_companion_session, stop.py's
    relaunch) already cross-check ground truth first.
    """

    def _call_start_claude(self, direction):
        with tempfile.TemporaryDirectory() as tmpdir:
            notif_path = os.path.join(tmpdir, "n.json")
            with patch.object(lifecycle, "_claude_cli_available", return_value=True), \
                 patch.object(lifecycle, "_find_all_claude_pids_by_project", return_value=[]), \
                 patch.object(lifecycle, "_load_allowed_tools", return_value=[]), \
                 patch.object(lifecycle, "_infer_direction", return_value=direction), \
                 patch.object(lifecycle, "_NOTIFICATION_PATH", notif_path), \
                 patch.object(lifecycle, "_spawn_terminal_app_fallback") as mock_spawn:
                lifecycle._start_claude(tmpdir)
            return mock_spawn.call_args[0][3]  # safe_prompt positional arg

    def test_high_confidence_direction_used_in_prompt(self):
        prompt = self._call_start_claude({
            "direction": "resume uncommitted work on: auth.py",
            "confidence": 0.95,
            "signal_source": "uncommitted_files",
        })
        self.assertIn("resume uncommitted work on", prompt)
        self.assertNotIn("execute the Next Action listed there immediately", prompt)

    def test_low_confidence_falls_back_to_generic_handover_prompt(self):
        prompt = self._call_start_claude({
            "direction": "",
            "confidence": 0.35,
            "signal_source": "none",
        })
        self.assertIn("execute the Next Action listed there immediately", prompt)


if __name__ == "__main__":
    unittest.main()
