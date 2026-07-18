"""
Tests for the smart-merge step (2026-07-16): create_checkpoint() reconciles
every currently-fresh sibling session's scratch handover into the one
canonical handover_<dev>.json/.md, via a single LLM call, only on a real
trigger (context/quota/idle). create_handover_only() (the every-turn light
path) writes to its own scratch file and never touches canonical or siblings
at all.

The one rule that matters most: a merge failure with real sibling data
present must leave the canonical file untouched rather than overwriting it
with a mechanical summary that silently drops every sibling's work. Same
"a nice step's failure must never corrupt the safety step" principle as the
git-push honesty fix earlier this session.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import checkpoint
from askr.state import writer


def _llm_summary(task="did a thing"):
    return {
        "task": task, "discussion_summary": "", "accomplishments": [], "in_progress": [],
        "next_actions": [], "decisions": [], "user_rejected_decisions": [],
        "failed_approaches": [], "files_in_play": [], "relational_files": [],
        "uncommitted_files": [], "blockers": [], "completed_goals": [], "behavioral_preferences": [],
        "session_metadata": {"trigger_type": "quota", "timestamp": "2026-07-16T00:00:00Z"},
    }


class SmartMergeTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.transcript_path = os.path.join(self._tmp.name, "t.jsonl")
        with open(self.transcript_path, "w") as f:
            f.write(json.dumps({"message": {"role": "user", "content": "hi"}}) + "\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _checkpoint_patches(self, llm_return):
        return [
            patch.object(checkpoint, "_generate_handover_with_llm", return_value=llm_return),
            patch.object(checkpoint, "_generate_project_brief"),
            patch.object(checkpoint, "_regenerate_architecture_md"),
            patch.object(checkpoint, "_infer_and_queue_tasks"),
            patch.object(checkpoint, "git_commit_push", return_value=(True, "")),
            patch.object(checkpoint, "_notify_discord_checkpoint"),
            patch("askr.state.analytics.record_session_end", return_value=0),
        ]


class SiblingScratchesReachTheLLMCallTests(SmartMergeTestBase):
    def test_create_checkpoint_passes_fresh_siblings_to_the_llm_call(self):
        writer.write_session_scratch_handover(_llm_summary("sibling's work"), "dev", "sess-sibling", state_dir=self.state_dir)

        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()) as mock_llm, \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push", return_value=(True, "")), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            checkpoint.create_checkpoint(
                trigger_type="quota", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-self",
            )

        _, kwargs = mock_llm.call_args
        self.assertEqual(len(kwargs.get("sibling_summaries") or []), 1)
        self.assertEqual(kwargs["sibling_summaries"][0]["task"], "sibling's work")

    def test_no_siblings_means_empty_sibling_summaries(self):
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()) as mock_llm, \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push", return_value=(True, "")), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            checkpoint.create_checkpoint(
                trigger_type="quota", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-self",
            )

        _, kwargs = mock_llm.call_args
        self.assertFalse(kwargs.get("sibling_summaries"))


class MergeFailureSafetyTests(SmartMergeTestBase):
    def test_merge_failure_with_siblings_leaves_canonical_untouched(self):
        canonical_path = os.path.join(self.state_dir, "handover_dev.json")
        with open(canonical_path, "w") as f:
            json.dump({"task": "the real existing canonical state"}, f)
        original_mtime = os.path.getmtime(canonical_path)

        writer.write_session_scratch_handover(_llm_summary("sibling's work"), "dev", "sess-sibling", state_dir=self.state_dir)

        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=None), \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push", return_value=(True, "")), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            result = checkpoint.create_checkpoint(
                trigger_type="quota", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-self",
            )

        self.assertTrue(result.get("merge_failed"))
        with open(canonical_path) as f:
            self.assertEqual(json.load(f)["task"], "the real existing canonical state")
        self.assertEqual(os.path.getmtime(canonical_path), original_mtime)

    def test_merge_failure_without_siblings_still_falls_back_mechanically(self):
        """Regression check: the single-session case (no siblings to merge)
        must keep today's existing behavior — mechanical fallback, not a
        withheld write. merge_required only kicks in when there's real
        sibling data that would otherwise be silently dropped."""
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=None), \
             patch.object(checkpoint, "_generate_project_brief"), \
             patch.object(checkpoint, "_regenerate_architecture_md"), \
             patch.object(checkpoint, "_infer_and_queue_tasks"), \
             patch.object(checkpoint, "git_commit_push", return_value=(True, "")), \
             patch.object(checkpoint, "_notify_discord_checkpoint"), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            result = checkpoint.create_checkpoint(
                trigger_type="quota", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-self",
            )

        self.assertFalse(result.get("merge_failed"))
        canonical_path = os.path.join(self.state_dir, "handover_dev.json")
        self.assertTrue(os.path.exists(canonical_path))


class LightHandoverWritesToScratchTests(SmartMergeTestBase):
    def test_create_handover_only_never_touches_canonical(self):
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            checkpoint.create_handover_only(
                trigger_type="stop", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-self",
            )

        self.assertFalse(os.path.exists(os.path.join(self.state_dir, "handover_dev.json")))
        self.assertTrue(os.path.exists(writer.scratch_handover_path("dev", "sess-self", state_dir=self.state_dir)))

    def test_two_concurrent_sessions_light_writes_do_not_clobber_each_other(self):
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary("session A")), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            checkpoint.create_handover_only(
                trigger_type="stop", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-a",
            )
        with patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary("session B")), \
             patch("askr.state.analytics.record_session_end", return_value=0):
            checkpoint.create_handover_only(
                trigger_type="stop", developer="dev",
                transcript_path=self.transcript_path, state_dir=self.state_dir,
                session_id="sess-b",
            )

        with open(writer.scratch_handover_path("dev", "sess-a", state_dir=self.state_dir)) as f:
            self.assertEqual(json.load(f)["task"], "session A")
        with open(writer.scratch_handover_path("dev", "sess-b", state_dir=self.state_dir)) as f:
            self.assertEqual(json.load(f)["task"], "session B")


if __name__ == "__main__":
    unittest.main()
