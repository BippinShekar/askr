"""
Tests for askr/cli/askr.py's `askr prefs` command family (Phase 3.9):
  askr prefs                       - list persisted rules
  askr prefs remove "rule"         - delete a persisted rule
  askr prefs pending               - list detected-but-unconfirmed candidates
  askr prefs keep "rule" --scope   - confirm a pending candidate (extension-invoked)
  askr prefs discard "rule"        - drop a pending candidate (extension-invoked)

Exercises cmd_prefs() end-to-end against real behavior_prefs file I/O (with
GLOBAL_CLAUDE_MD/pending-store paths redirected to a temp dir and cwd
chdir'd into a temp project dir), the same style as test_claude_md_guard.py.
Console output isn't asserted — only the resulting state.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli.askr import cmd_prefs
from askr.state import behavior_prefs as bp


class CmdPrefsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = os.path.join(self._tmp.name, "project")
        os.makedirs(self.project_dir)
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

        self._global_md = os.path.join(self._tmp.name, "global_CLAUDE.md")
        self._pending_path = os.path.join(self._tmp.name, "behavior_pending.json")

        self._patches = [
            patch.object(bp, "GLOBAL_CLAUDE_MD", self._global_md),
            patch.object(bp, "_PENDING_PATH", self._pending_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def test_bare_prefs_does_not_crash_with_nothing_persisted(self):
        cmd_prefs([])  # just must not raise

    def test_remove_deletes_a_persisted_rule(self):
        bp.write_rule("Always build in stages", "project")
        cmd_prefs(["remove", "Always build in stages"])
        self.assertEqual(bp.read_persisted_rules("project"), [])

    def test_remove_missing_rule_does_not_crash(self):
        cmd_prefs(["remove", "Never persisted"])  # must not raise

    def test_remove_without_text_shows_usage_and_does_not_crash(self):
        cmd_prefs(["remove"])  # must not raise

    def test_pending_lists_detected_candidates(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        cmd_prefs(["pending"])  # must not raise; state already verified via bp directly
        self.assertEqual(len(bp.load_pending()), 1)

    def test_keep_persists_rule_and_clears_pending(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        cmd_prefs(["keep", "Always build in stages", "--scope", "global"])
        self.assertEqual(bp.read_persisted_rules("global"), ["Always build in stages"])
        self.assertEqual(bp.load_pending(), [])

    def test_keep_defaults_to_project_scope_without_flag(self):
        cmd_prefs(["keep", "Some rule"])
        self.assertEqual(bp.read_persisted_rules("project"), ["Some rule"])
        self.assertEqual(bp.read_persisted_rules("global"), [])

    def test_discard_clears_pending_without_persisting(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        cmd_prefs(["discard", "Always build in stages"])
        self.assertEqual(bp.load_pending(), [])
        self.assertEqual(bp.read_persisted_rules("global"), [])
        self.assertEqual(bp.read_persisted_rules("project"), [])

    def test_unknown_subcommand_does_not_crash(self):
        cmd_prefs(["bogus"])  # must not raise


if __name__ == "__main__":
    unittest.main()
