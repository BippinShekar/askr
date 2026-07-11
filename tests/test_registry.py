"""
Tests for askr/session/registry.py's is_session_confirmed_dead() — the fix
for a third recurrence of the same underlying bug in
lifecycle._prune_companioned_sessions (2026-07-09, then twice on
2026-07-11). Each fix addressed a way "is this session still alive" could
be answered wrong:

  1. Stats freshness (SESSION_STALE_SECS) lapses when the Mac sleeps or a
     window sits idle, not just when a session ends.
  2. A registry-PID check (is_session_pid_alive, this function's immediate
     predecessor) fixed that, but treated "no registry entry" the same as
     "confirmed dead" — and registration turns out to be unreliable: of
     dozens of distinct sessions active in one day, only one had an entry.

is_session_confirmed_dead requires POSITIVE proof of death. "No entry" and
"no confirmable PID" both mean "leave it alone," not "gone" — the
asymmetry is deliberate: never wrongly pruning a live session matters far
more than eventually forgetting a truly dead one.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import registry


class IsSessionConfirmedDeadTests(unittest.TestCase):
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

    def test_missing_entry_is_not_confirmed_dead(self):
        # The core fix: no registry entry (registration never fired, or
        # predates registration existing) must NOT be treated as dead.
        self.assertFalse(registry.is_session_confirmed_dead("no-such-session"))

    def test_empty_session_id_is_not_confirmed_dead(self):
        self.assertFalse(registry.is_session_confirmed_dead(""))

    def test_live_pid_is_not_confirmed_dead(self):
        self._write_entry("sess-1", pid=os.getpid())  # our own process, definitely alive
        self.assertFalse(registry.is_session_confirmed_dead("sess-1"))

    def test_dead_pid_is_confirmed_dead(self):
        # An implausibly large PID reliably doesn't exist.
        self._write_entry("sess-1", pid=999999)
        self.assertTrue(registry.is_session_confirmed_dead("sess-1"))

    def test_stale_heartbeat_does_not_matter(self):
        # Heartbeat age is irrelevant here, unlike registry._is_alive used
        # elsewhere for sibling detection — a suspended process (Mac asleep)
        # has a stale heartbeat and a perfectly live PID.
        self._write_entry("sess-1", pid=os.getpid(), last_heartbeat="2020-01-01T00:00:00+00:00")
        self.assertFalse(registry.is_session_confirmed_dead("sess-1"))

    def test_missing_pid_field_is_not_confirmed_dead(self):
        self._write_entry("sess-1", pid=None)
        self.assertFalse(registry.is_session_confirmed_dead("sess-1"))

    def test_corrupt_entry_file_fails_safe(self):
        path = os.path.join(self._tmp.name, "sess-1.json")
        with open(path, "w") as f:
            f.write("not json")
        self.assertFalse(registry.is_session_confirmed_dead("sess-1"))


if __name__ == "__main__":
    unittest.main()
