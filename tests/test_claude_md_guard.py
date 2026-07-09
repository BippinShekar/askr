"""
Tests for askr/cli/askr.py's _install_claude_md() — Phase 3.13 S5.

Confirms the guard section template (and therefore what `askr init` writes
into a project's CLAUDE.md) mentions rejected_decisions.jsonl alongside the
existing decisions.jsonl/failed_approaches.md checks, that user content
outside the fenced markers survives an update, and that the install is
idempotent (second run reports "unchanged").
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli.askr import (
    _install_claude_md,
    _CLAUDE_MD_GUARD_SECTION,
    _CLAUDE_MD_GUARD_START,
    _CLAUDE_MD_GUARD_END,
)


class InstallClaudeMdGuardSectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _read_claude_md(self):
        with open(os.path.join(self.project_dir, "CLAUDE.md")) as f:
            return f.read()

    def test_template_mentions_rejected_decisions_jsonl(self):
        self.assertIn("rejected_decisions.jsonl", _CLAUDE_MD_GUARD_SECTION)

    def test_template_still_mentions_existing_checks(self):
        self.assertIn("decisions.jsonl", _CLAUDE_MD_GUARD_SECTION)
        self.assertIn("failed_approaches.md", _CLAUDE_MD_GUARD_SECTION)

    def test_fresh_install_writes_rejected_decisions_check(self):
        result = _install_claude_md()
        self.assertEqual(result, "created")
        content = self._read_claude_md()
        self.assertIn("rejected_decisions.jsonl", content)
        self.assertIn(_CLAUDE_MD_GUARD_START, content)
        self.assertIn(_CLAUDE_MD_GUARD_END, content)

    def test_update_preserves_user_content_outside_markers(self):
        with open("CLAUDE.md", "w") as f:
            f.write("# My Project\n\nSome hand-written notes here.\n")
        _install_claude_md()
        content = self._read_claude_md()
        self.assertIn("Some hand-written notes here.", content)
        self.assertIn("rejected_decisions.jsonl", content)

    def test_old_guard_section_is_upgraded_to_mention_rejections(self):
        old_section = (
            f"{_CLAUDE_MD_GUARD_START}\n"
            "## Implementation Guard\n\n"
            "Before editing any file:\n"
            "1. Check `askr_state/decisions.jsonl` for settled decisions that affect that file's domain.\n"
            "2. Check `askr_state/failed_approaches.md` for approaches already tried and rejected.\n"
            "3. If your planned change contradicts a settled decision or repeats a rejected approach, say so explicitly before implementing — do not proceed silently.\n"
            f"{_CLAUDE_MD_GUARD_END}"
        )
        with open("CLAUDE.md", "w") as f:
            f.write(old_section + "\n")

        result = _install_claude_md()
        self.assertEqual(result, "updated")
        content = self._read_claude_md()
        self.assertIn("rejected_decisions.jsonl", content)

    def test_second_run_is_idempotent(self):
        _install_claude_md()
        result = _install_claude_md()
        self.assertEqual(result, "unchanged")

    def test_no_file_exists_yet_returns_created(self):
        self.assertFalse(os.path.exists("CLAUDE.md"))
        result = _install_claude_md()
        self.assertEqual(result, "created")


if __name__ == "__main__":
    unittest.main()
