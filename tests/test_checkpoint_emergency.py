"""
Regression test: PreCompact ("emergency") checkpoints must go through the same
real LLM handover path as every other trigger_type, not a hardcoded boilerplate
string. The old emergency branch also referenced transcript_text before it was
ever assigned (only assigned in the non-emergency branch) — an UnboundLocalError
waiting to happen the first time _infer_and_queue_tasks ran for a real emergency
checkpoint.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import checkpoint


class EmergencyCheckpointRoutingTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)

        self.transcript_path = os.path.join(self._tmp.name, "transcript.jsonl")
        with open(self.transcript_path, "w") as f:
            f.write(json.dumps({
                "message": {"role": "user", "content": [{"type": "text", "text": "fix the bug"}]}
            }) + "\n")
            f.write(json.dumps({
                "message": {"role": "assistant", "content": [{"type": "text", "text": "done"}]}
            }) + "\n")

    def tearDown(self):
        self._tmp.cleanup()

    def test_emergency_uses_llm_handover_not_hardcoded_string(self):
        llm_summary = {
            "task": "Fixed the bug",
            "discussion_summary": "x",
            "accomplishments": [],
            "in_progress": [],
            "next_actions": [],
            "decisions": [],
            "user_rejected_decisions": [],
            "failed_approaches": [],
            "files_in_play": [],
            "relational_files": [],
            "uncommitted_files": [],
            "blockers": [],
            "completed_goals": [],
            "session_metadata": {"trigger_type": "emergency", "timestamp": "2026-07-02T00:00:00Z"},
        }

        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=llm_summary) as mock_llm, \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push"), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):

            result = checkpoint.create_checkpoint(
                trigger_type="emergency",
                developer="testdev",
                transcript_path=self.transcript_path,
                state_dir=self.state_dir,
                session_id="sess1",
            )

        # The real LLM path was invoked (proves emergency no longer short-circuits
        # to hardcoded boilerplate, and transcript_text was built without error).
        mock_llm.assert_called_once()
        _, kwargs = mock_llm.call_args
        self.assertEqual(kwargs.get("trigger_type"), "emergency")

        # write_handover took the dict path -> handover_<dev>.json exists and
        # contains the LLM-generated task, not the old hardcoded string.
        json_path = os.path.join(self.state_dir, "handover_testdev.json")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path) as f:
            written = json.load(f)
        self.assertEqual(written["task"], "Fixed the bug")
        self.assertNotIn("Emergency checkpoint triggered", json.dumps(written))

        self.assertEqual(result["trigger"], "emergency")

    def test_emergency_falls_back_to_mechanical_summary_when_llm_unavailable(self):
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=None) as mock_llm, \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push"), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):

            checkpoint.create_checkpoint(
                trigger_type="emergency",
                developer="testdev",
                transcript_path=self.transcript_path,
                state_dir=self.state_dir,
                session_id="sess1",
            )

        mock_llm.assert_called_once()

        json_path = os.path.join(self.state_dir, "handover_testdev.json")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path) as f:
            written = json.load(f)
        self.assertTrue(written.get("session_metadata", {}).get("degraded"))


if __name__ == "__main__":
    unittest.main()
