"""
Tests for askr/session/registry.py's is_session_pid_alive() — added
2026-07-11 as the fix for a real incident: lifecycle.py's
_prune_companioned_sessions used to check stats freshness (SESSION_STALE_SECS,
10 min), which lapses whenever the Mac sleeps or a window sits idle, not just
when a session truly ends. Waking the machine after any longer nap made a
still-open session look brand new to the companioned_sessions dedup and
re-fired a companion for the exact same window. PID-only liveness (no
heartbeat freshness requirement, unlike _is_alive/get_active_sessions) fixes
this: a suspended process keeps a valid PID until it actually exits.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import registry


class IsSessionPidAliveTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._patch = patch.object(registry, "_sessions_dir", return_value=self._tmp.name)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def _write_entry(self, session_id, pid=None, last_heartbeat=None):
        entry = {"session_id": session_id, "pid": pid, "last_heartbeat": last_heartbeat}
        with open(os.path.join(self._tmp.name, f"{session_id}.json"), "w") as f:
            json.dump(entry, f)

    def test_missing_entry_is_not_alive(self):
        self.assertFalse(registry.is_session_pid_alive("no-such-session"))

    def test_empty_session_id_is_not_alive(self):
        self.assertFalse(registry.is_session_pid_alive(""))

    def test_live_pid_is_alive(self):
        self._write_entry("sess-1", pid=os.getpid())  # our own process, definitely alive
        self.assertTrue(registry.is_session_pid_alive("sess-1"))

    def test_dead_pid_is_not_alive(self):
        # PID 1 owned by root is a permission error (still "alive" from our
        # process's view via kill -0 semantics being EPERM not ESRCH) — use
        # an implausibly large PID instead, which reliably doesn't exist.
        self._write_entry("sess-1", pid=999999)
        self.assertFalse(registry.is_session_pid_alive("sess-1"))

    def test_stale_heartbeat_does_not_matter(self):
        # The whole point of this function: heartbeat age is irrelevant,
        # unlike registry._is_alive used elsewhere for sibling detection.
        self._write_entry("sess-1", pid=os.getpid(), last_heartbeat="2020-01-01T00:00:00+00:00")
        self.assertTrue(registry.is_session_pid_alive("sess-1"))

    def test_missing_pid_field_is_not_alive(self):
        self._write_entry("sess-1", pid=None)
        self.assertFalse(registry.is_session_pid_alive("sess-1"))

    def test_corrupt_entry_file_fails_safe(self):
        path = os.path.join(self._tmp.name, "sess-1.json")
        with open(path, "w") as f:
            f.write("not json")
        self.assertFalse(registry.is_session_pid_alive("sess-1"))


if __name__ == "__main__":
    unittest.main()
