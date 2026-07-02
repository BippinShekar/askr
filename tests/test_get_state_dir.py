"""
Tests for askr/state/config.py's get_state_dir() and has_claude_segment().

Covers the nested-worktree root-hijack bug: a git worktree (e.g. Claude
Code's isolation:"worktree" fork mechanism, checked out under
<root>/.claude/worktrees/<id>/) is a full checkout of every tracked path,
including askr_state/ itself. Before this fix, if cwd drifted into one of
these, get_state_dir()'s cwd-relative walk-up would pick the worktree's
duplicate askr_state/ as project root instead of continuing up to the real
one — corrupting state writes and, via pre_tool_use.py's cross-repo guard
(which derives project_root from get_state_dir()), locking the session out
of its own real root (even plain `cd ..` got blocked as "cross-repo").
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import config


class HasClaudeSegmentTests(unittest.TestCase):
    def test_no_claude_segment(self):
        self.assertFalse(config.has_claude_segment("/Users/bippin/Desktop/askr"))

    def test_claude_segment_present(self):
        self.assertTrue(
            config.has_claude_segment("/Users/bippin/Desktop/askr/.claude/worktrees/agent-x")
        )

    def test_claude_as_substring_not_segment_is_not_matched(self):
        # ".claudexyz" is a different directory name, not the .claude segment
        self.assertFalse(config.has_claude_segment("/Users/bippin/Desktop/askr/.claudexyz"))


class GetStateDirNestedWorktreeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "askr_state"), exist_ok=True)

        # Simulate a git worktree checkout of the same project under .claude/worktrees/
        self.worktree = os.path.join(self.root, ".claude", "worktrees", "agent-x")
        os.makedirs(os.path.join(self.worktree, "askr_state"), exist_ok=True)

        self._orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def test_cwd_at_real_root_resolves_to_real_root(self):
        os.chdir(self.root)
        self.assertEqual(
            os.path.realpath(config.get_state_dir()),
            os.path.realpath(os.path.join(self.root, "askr_state")),
        )

    def test_cwd_inside_nested_worktree_skips_worktree_and_finds_real_root(self):
        os.chdir(self.worktree)
        self.assertEqual(
            os.path.realpath(config.get_state_dir()),
            os.path.realpath(os.path.join(self.root, "askr_state")),
        )


if __name__ == "__main__":
    unittest.main()
