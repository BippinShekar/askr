"""
Tests for `askr guard approve/discard/list` (2026-08-15) — the escape-hatch
redesign. pre_tool_use.py's guard used to auto-allow a write through after
2 blocks with only an after-the-fact Discord message; confirmed in real use
(twice) that Claude retrying twice is not evidence a human ever reviewed
the approach. Now the write is held (guard_blocks.json's pending_approval
flag) until one of these two commands actually runs.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli import askr


class CmdGuardTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._blocks_path = os.path.join(self._tmp.name, "guard_blocks.json")
        self._orig_path = askr._GUARD_BLOCKS_PATH
        askr._GUARD_BLOCKS_PATH = self._blocks_path

    def tearDown(self):
        askr._GUARD_BLOCKS_PATH = self._orig_path
        self._tmp.cleanup()

    def _write_blocks(self, blocks):
        with open(self._blocks_path, "w") as f:
            json.dump(blocks, f)

    def _read_blocks(self):
        with open(self._blocks_path) as f:
            return json.load(f)

    def test_list_with_no_pending_says_so(self):
        self._write_blocks({})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["list"])
        self.assertIn("no writes pending approval", buf.getvalue())

    def test_list_shows_pending_entries_with_issues(self):
        self._write_blocks({
            "/proj/bad.py": {"pending_approval": True, "count": 2, "issues": ["contradicts architecture.md"]},
            "/proj/fine.py": {"pending_approval": False, "count": 1},
        })
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["list"])
        output = buf.getvalue()
        self.assertIn("bad.py", output)
        self.assertIn("contradicts architecture.md", output)
        self.assertNotIn("fine.py", output)  # not pending — must not show

    def test_approve_missing_file_arg_shows_usage(self):
        self._write_blocks({})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["approve"])
        self.assertIn("usage", buf.getvalue().lower())

    def test_approve_nonexistent_entry_says_nothing_pending(self):
        self._write_blocks({})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["approve", "/proj/nothing.py"])
        self.assertIn("nothing pending approval", buf.getvalue())

    def test_approve_sets_approved_flag_clears_pending(self):
        self._write_blocks({"/proj/bad.py": {"pending_approval": True, "count": 2, "issues": []}})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["approve", "/proj/bad.py"])
        self.assertIn("approved", buf.getvalue())
        entry = self._read_blocks()["/proj/bad.py"]
        self.assertTrue(entry["approved"])
        self.assertFalse(entry["pending_approval"])

    def test_discard_removes_the_entry_entirely(self):
        self._write_blocks({"/proj/bad.py": {"pending_approval": True, "count": 2, "issues": []}})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["discard", "/proj/bad.py"])
        self.assertIn("discarded", buf.getvalue())
        self.assertNotIn("/proj/bad.py", self._read_blocks())

    def test_discard_nonexistent_entry_says_nothing_pending(self):
        self._write_blocks({})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["discard", "/proj/nothing.py"])
        self.assertIn("nothing pending approval", buf.getvalue())

    def test_approve_on_entry_not_actually_pending_is_refused(self):
        # count exists but pending_approval is False — must not silently approve
        # something that was never actually held.
        self._write_blocks({"/proj/bad.py": {"pending_approval": False, "count": 1}})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["approve", "/proj/bad.py"])
        self.assertIn("nothing pending approval", buf.getvalue())

    def test_no_subcommand_shows_help(self):
        self._write_blocks({})
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard([])
        output = buf.getvalue()
        self.assertIn("askr guard list", output)
        self.assertIn("askr guard approve", output)
        self.assertIn("askr guard discard", output)

    def test_missing_blocks_file_treated_as_empty(self):
        # Don't write the file at all.
        buf = io.StringIO()
        with redirect_stdout(buf):
            askr.cmd_guard(["list"])
        self.assertIn("no writes pending approval", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
