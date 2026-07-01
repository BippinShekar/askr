"""
Tests for the queue-holding side of the Phase 5 approval gate:
session_start.py's peek/approval-flag helpers and askr.py's approve/discard
commands. Covers the property the roadmap calls out explicitly — a held
task must never be silently dropped.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import session_start
from askr.cli import askr as askr_cli


class TaskApprovalGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_cwd = os.getcwd()
        os.chdir(self._tmp.name)
        os.makedirs(os.path.join(self._tmp.name, "askr_state", "tasks"), exist_ok=True)
        self.queue_path = os.path.join(self._tmp.name, "askr_state", "tasks", "queue_dev.jsonl")

        self._notif_tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._orig_notif_path = session_start._NOTIFICATION_PATH
        session_start._NOTIFICATION_PATH = self._notif_tmp.name

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()
        session_start._NOTIFICATION_PATH = self._orig_notif_path
        try:
            os.remove(self._notif_tmp.name)
        except Exception:
            pass

    def _write_queue(self, tasks):
        with open(self.queue_path, "w") as f:
            for t in tasks:
                f.write(json.dumps(t) + "\n")

    def test_peek_does_not_truncate_queue(self):
        self._write_queue([{"id": "1", "desc": "do the thing", "from": "alice"}])
        tasks = session_start._peek_task_queue("dev")
        self.assertEqual(len(tasks), 1)
        # peek must be non-destructive — the queue file is untouched
        with open(self.queue_path) as f:
            self.assertEqual(len(f.readlines()), 1)

    def test_peek_empty_queue_returns_empty(self):
        self.assertEqual(session_start._peek_task_queue("dev"), [])

    def test_approval_flag_is_one_shot(self):
        self.assertFalse(session_start._consume_approval_flag("dev"))
        askr_cli._approve_held_tasks("dev")
        self.assertTrue(session_start._consume_approval_flag("dev"))
        # consumed — a second check must not find it again
        self.assertFalse(session_start._consume_approval_flag("dev"))

    def test_notify_writes_task_approval_pending_payload(self):
        tasks = [{"id": "1", "desc": "do the thing", "from": "alice"}]
        session_start._notify_tasks_held("dev", tasks, ["--dangerously-skip-permissions in session launch args"])
        with open(session_start._NOTIFICATION_PATH) as f:
            payload = json.load(f)
        self.assertEqual(payload["type"], "task_approval_pending")
        self.assertEqual(payload["developer"], "dev")
        self.assertIn("do the thing", payload["message"])

    def test_discard_archives_and_clears_queue(self):
        self._write_queue([{"id": "1", "desc": "do the thing", "from": "alice"}])
        n = askr_cli._discard_held_tasks("dev")
        self.assertEqual(n, 1)

        with open(self.queue_path) as f:
            self.assertEqual(f.read(), "")

        discard_path = os.path.join(self._tmp.name, "askr_state", "tasks", "discarded_dev.jsonl")
        with open(discard_path) as f:
            archived = json.loads(f.readline())
        self.assertEqual(archived["desc"], "do the thing")
        self.assertIn("discarded_at", archived)

    def test_discard_empty_queue_is_noop(self):
        self.assertEqual(askr_cli._discard_held_tasks("dev"), 0)


if __name__ == "__main__":
    unittest.main()
