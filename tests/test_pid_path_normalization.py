"""
Regression test for the companion-dedup miscount (2026-08-18): macOS mounts
the boot volume at both /Users/... and the underlying
/System/Volumes/Data/Users/... — `lsof -d cwd` reports whichever form the
kernel resolved to, which doesn't always match the form the caller built
project_path from. A bare string comparison silently undercounts live pids,
which is exactly what let pre_compact.py's should_open_companion guard open
a redundant companion on top of one already running.

Uses a real temp-dir symlink (not the actual macOS volume mount, which is
environment-specific) so the test exercises the same symlink-mismatch shape
portably.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.lifecycle import _find_all_claude_pids_by_project, _norm_path


class NormPathTests(unittest.TestCase):
    def test_symlink_and_real_path_normalize_equal(self):
        with tempfile.TemporaryDirectory() as real_dir:
            link_dir = real_dir.rstrip("/") + "-link"
            os.symlink(real_dir, link_dir)
            try:
                self.assertEqual(_norm_path(real_dir), _norm_path(link_dir))
            finally:
                os.remove(link_dir)


class FindAllClaudePidsByProjectTests(unittest.TestCase):
    def test_matches_pid_when_lsof_reports_symlinked_form(self):
        """
        Caller passes the real (unresolved) project_path; lsof reports the
        process's cwd via a symlinked alias to that same directory. Before
        the fix, the exact-string comparison missed this and returned [],
        making an already-running session invisible to the dedup guard.
        """
        with tempfile.TemporaryDirectory() as real_dir:
            link_dir = real_dir.rstrip("/") + "-link"
            os.symlink(real_dir, link_dir)
            try:
                def fake_run(cmd, **kwargs):
                    from unittest.mock import MagicMock
                    result = MagicMock()
                    if cmd[0] == "pgrep":
                        result.stdout = "4242\n"
                    elif cmd[0] == "lsof":
                        result.stdout = f"n{link_dir}\n"
                    return result

                with patch("askr.session.lifecycle.subprocess.run", side_effect=fake_run):
                    pids = _find_all_claude_pids_by_project(real_dir)
                self.assertEqual(pids, [4242])
            finally:
                os.remove(link_dir)

    def test_no_match_for_genuinely_different_project(self):
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            def fake_run(cmd, **kwargs):
                from unittest.mock import MagicMock
                result = MagicMock()
                if cmd[0] == "pgrep":
                    result.stdout = "4242\n"
                elif cmd[0] == "lsof":
                    result.stdout = f"n{dir_b}\n"
                return result

            with patch("askr.session.lifecycle.subprocess.run", side_effect=fake_run):
                pids = _find_all_claude_pids_by_project(dir_a)
            self.assertEqual(pids, [])


if __name__ == "__main__":
    unittest.main()
