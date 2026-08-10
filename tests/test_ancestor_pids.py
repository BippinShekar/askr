"""
Tests for lifecycle._get_ancestor_pids (2026-08-11) — the Python half of the
same-session rate-limit-resume feature's terminal-targeting bridge.

vscode.Terminal exposes terminal.processId (the shell PID), not a Claude
session_id. Python already knows how to go transcript_path -> claude PID
(_find_session_pid); this walks the process tree upward from that PID so
the extension can match ANY of the returned ancestors against
terminal.processId, without needing to specifically identify which one is
"the shell" — real process trees can have extra layers (wrappers, tmux).

Uses real spawned subprocesses (not mocked `ps` output) so the actual
process-tree walk is exercised end to end, not just the parsing logic.
"""

import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.lifecycle import _get_ancestor_pids


class RealProcessTreeTests(unittest.TestCase):
    def setUp(self):
        # Spawn a real 2-level process tree: this test process -> shell ->
        # sleep. `bash -c 'sleep 30'` makes bash exec into sleep on most
        # platforms (replacing the shell's own PID), so guard for either
        # shape by walking from the leaf and asserting our own PID is
        # somewhere in the ancestor chain, not asserting an exact depth.
        self.child = subprocess.Popen(
            ["/bin/sh", "-c", "sleep 30"],
        )
        time.sleep(0.2)  # let the child actually start before we inspect it

    def tearDown(self):
        self.child.terminate()
        try:
            self.child.wait(timeout=3)
        except Exception:
            self.child.kill()

    def test_immediate_child_ancestor_chain_includes_this_process(self):
        ancestors = _get_ancestor_pids(self.child.pid)
        self.assertIn(os.getpid(), ancestors)

    def test_ancestor_order_is_nearest_first(self):
        ancestors = _get_ancestor_pids(self.child.pid)
        # This test process must appear before its own ancestors (e.g. the
        # test runner's parent) in the returned list.
        self.assertEqual(ancestors[0], os.getpid())

    def test_max_depth_bounds_the_walk(self):
        ancestors = _get_ancestor_pids(self.child.pid, max_depth=1)
        self.assertEqual(len(ancestors), 1)
        self.assertEqual(ancestors[0], os.getpid())

    def test_already_exited_pid_returns_empty_list_not_raises(self):
        dead = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
        dead.wait()
        try:
            ancestors = _get_ancestor_pids(dead.pid)
        except Exception as e:
            self.fail(f"_get_ancestor_pids raised on an exited pid: {e}")
        self.assertIsInstance(ancestors, list)


class MockedPsTests(unittest.TestCase):
    """Deterministic coverage for edge cases real subprocess trees can't
    reliably produce on demand (init/launchd boundary, ps failures)."""

    def _mock_ps(self, chain):
        """chain: {pid: ppid}. A pid missing from the dict simulates ps
        returning nothing (process gone)."""
        def _run(cmd, **kwargs):
            result = type("R", (), {})()
            pid = int(cmd[-1])
            if pid in chain:
                result.stdout = str(chain[pid])
            else:
                result.stdout = ""
            return result
        return _run

    def test_stops_at_pid_1(self):
        chain = {100: 50, 50: 1}
        with patch("askr.session.lifecycle.subprocess.run", side_effect=self._mock_ps(chain)):
            ancestors = _get_ancestor_pids(100)
        self.assertEqual(ancestors, [50])

    def test_stops_when_ps_returns_nothing(self):
        chain = {100: 50}  # 50's own ppid lookup returns nothing
        with patch("askr.session.lifecycle.subprocess.run", side_effect=self._mock_ps(chain)):
            ancestors = _get_ancestor_pids(100)
        self.assertEqual(ancestors, [50])

    def test_ps_exception_fails_closed_to_empty_list(self):
        with patch("askr.session.lifecycle.subprocess.run", side_effect=Exception("boom")):
            try:
                ancestors = _get_ancestor_pids(100)
            except Exception as e:
                self.fail(f"_get_ancestor_pids raised: {e}")
        self.assertEqual(ancestors, [])

    def test_respects_max_depth_with_a_long_chain(self):
        chain = {i: i - 1 for i in range(100, 90, -1)}
        chain[91] = 90
        with patch("askr.session.lifecycle.subprocess.run", side_effect=self._mock_ps(chain)):
            ancestors = _get_ancestor_pids(100, max_depth=3)
        self.assertEqual(len(ancestors), 3)


if __name__ == "__main__":
    unittest.main()
