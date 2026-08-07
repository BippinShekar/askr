"""
Tests for the deterministic next_actions staleness filter (2026-08-08):
checkpoint._load_accomplished_corpus() + checkpoint._drop_accomplished_next_actions().

Same quality bar as the scratch-handover smart merge (test_smart_merge.py):
real structured signal — accomplishments[]/completed_goals[] pulled from past
handover_<dev>.json commits via `git show`, not a commit-message guess bounded
by a shallow `git log --oneline -15` window — instead of blind trust that the
LLM will notice a completion from many sessions ago. And the same fail-closed
principle: any error in the corpus load or the filter must leave next_actions
exactly as they were, never silently drop something that couldn't be verified.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import checkpoint
from askr.state import writer


def _llm_summary(task="did a thing"):
    return {
        "task": task, "discussion_summary": "", "accomplishments": [], "in_progress": [],
        "next_actions": [], "decisions": [], "user_rejected_decisions": [],
        "failed_approaches": [], "files_in_play": [], "relational_files": [],
        "uncommitted_files": [], "blockers": [], "completed_goals": [], "behavioral_preferences": [],
        "session_metadata": {"trigger_type": "quota", "timestamp": "2026-08-08T00:00:00Z"},
    }


# ---------------------------------------------------------------------------
# _drop_accomplished_next_actions — pure function, no I/O
# ---------------------------------------------------------------------------

class DropAccomplishedNextActionsTests(unittest.TestCase):
    def test_matched_action_is_dropped(self):
        next_actions = [{"action": "Build structured JSONL event log for trigger and companion lineage"}]
        corpus = ["add structured JSONL event log for trigger companion lineage"]
        self.assertEqual(checkpoint._drop_accomplished_next_actions(next_actions, corpus), [])

    def test_unmatched_action_survives(self):
        next_actions = [{"action": "Build a visualization dashboard for the session event log"}]
        corpus = ["fixed idle-trigger dedup keying on project_path and session_id"]
        result = checkpoint._drop_accomplished_next_actions(next_actions, corpus)
        self.assertEqual(result, next_actions)

    def test_partial_overlap_below_threshold_survives(self):
        next_actions = [{"action": "Refactor the quota polling loop to run independent of session activity"}]
        corpus = ["fixed a typo in the readme"]
        result = checkpoint._drop_accomplished_next_actions(next_actions, corpus)
        self.assertEqual(result, next_actions)

    def test_empty_corpus_is_noop(self):
        next_actions = [{"action": "do X"}]
        self.assertEqual(checkpoint._drop_accomplished_next_actions(next_actions, []), next_actions)

    def test_empty_next_actions_is_noop(self):
        self.assertEqual(checkpoint._drop_accomplished_next_actions([], ["something done"]), [])

    def test_corpus_of_only_stopword_length_tokens_is_noop(self):
        # corpus strings that tokenize to nothing (too short) must not crash
        # and must not match everything.
        next_actions = [{"action": "Build the graph dashboard"}]
        result = checkpoint._drop_accomplished_next_actions(next_actions, ["ok", "hi", "x"])
        self.assertEqual(result, next_actions)

    def test_string_next_action_handled_without_action_key(self):
        next_actions = ["build the session event graph dashboard"]
        corpus = ["built the session event graph dashboard for daily review"]
        self.assertEqual(checkpoint._drop_accomplished_next_actions(next_actions, corpus), [])

    def test_next_action_missing_action_key_survives(self):
        next_actions = [{"order": 1}]
        result = checkpoint._drop_accomplished_next_actions(next_actions, ["something done"])
        self.assertEqual(result, next_actions)

    def test_mixed_batch_only_matched_ones_dropped(self):
        next_actions = [
            {"order": 1, "action": "Build structured JSONL event log for trigger and companion lineage"},
            {"order": 2, "action": "Build a visualization dashboard for the session event log"},
        ]
        corpus = ["add structured JSONL event log for trigger companion lineage"]
        result = checkpoint._drop_accomplished_next_actions(next_actions, corpus)
        self.assertEqual(result, [next_actions[1]])


# ---------------------------------------------------------------------------
# _load_accomplished_corpus — git history walk, mocked subprocess
# ---------------------------------------------------------------------------

class LoadAccomplishedCorpusTests(unittest.TestCase):
    def setUp(self):
        checkpoint._accomplished_corpus_cache.clear()

    def tearDown(self):
        checkpoint._accomplished_corpus_cache.clear()

    @staticmethod
    def _mock_git(hashes, shows):
        """hashes: list[str] (git log output). shows: {hash: dict|None} — None simulates
        a failed `git show` (non-zero exit)."""
        def _run(cmd, **kwargs):
            result = MagicMock()
            if cmd[:2] == ["git", "log"]:
                result.stdout = "\n".join(hashes)
                result.returncode = 0
            elif cmd[:2] == ["git", "show"]:
                h = cmd[2].split(":")[0]
                data = shows.get(h)
                if data is None:
                    result.returncode = 1
                    result.stdout = ""
                else:
                    result.returncode = 0
                    result.stdout = json.dumps(data)
            else:
                result.returncode = 1
                result.stdout = ""
            return result
        return _run

    def test_collects_accomplishments_and_completed_goals(self):
        shows = {"h1": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": ["goal A"]}}
        with patch("askr.session.checkpoint.subprocess.run", side_effect=self._mock_git(["h1"], shows)):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertIn("did thing A", corpus)
        self.assertIn("goal A", corpus)

    def test_dedupes_identical_strings_across_commits(self):
        shows = {
            "h1": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": []},
            "h2": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": []},
        }
        with patch("askr.session.checkpoint.subprocess.run", side_effect=self._mock_git(["h1", "h2"], shows)):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertEqual(corpus.count("did thing A"), 1)

    def test_not_done_accomplishment_excluded(self):
        shows = {"h1": {"accomplishments": [{"what": "in flight thing", "done": False}], "completed_goals": []}}
        with patch("askr.session.checkpoint.subprocess.run", side_effect=self._mock_git(["h1"], shows)):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertNotIn("in flight thing", corpus)

    def test_one_failed_show_does_not_break_the_rest(self):
        shows = {"h1": None, "h2": {"accomplishments": [{"what": "did thing B", "done": True}], "completed_goals": []}}
        with patch("askr.session.checkpoint.subprocess.run", side_effect=self._mock_git(["h1", "h2"], shows)):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertIn("did thing B", corpus)

    def test_malformed_json_in_show_is_skipped_not_raised(self):
        def _run(cmd, **kwargs):
            result = MagicMock()
            if cmd[:2] == ["git", "log"]:
                result.stdout = "h1"
                result.returncode = 0
            else:
                result.returncode = 0
                result.stdout = "not json"
            return result
        with patch("askr.session.checkpoint.subprocess.run", side_effect=_run):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertEqual(corpus, [])

    def test_git_raising_returns_empty_not_exception(self):
        with patch("askr.session.checkpoint.subprocess.run", side_effect=Exception("boom")):
            try:
                corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
            except Exception as e:
                self.fail(f"_load_accomplished_corpus raised: {e}")
        self.assertEqual(corpus, [])

    def test_no_commit_history_returns_empty(self):
        with patch("askr.session.checkpoint.subprocess.run", side_effect=self._mock_git([], {})):
            corpus = checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertEqual(corpus, [])

    def test_cache_hit_within_ttl_skips_subprocess(self):
        shows = {"h1": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": []}}
        mock_run = MagicMock(side_effect=self._mock_git(["h1"], shows))
        with patch("askr.session.checkpoint.subprocess.run", mock_run):
            checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
            calls_after_first = mock_run.call_count
            checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertEqual(mock_run.call_count, calls_after_first)

    def test_cache_expired_after_ttl_re_invokes_subprocess(self):
        shows = {"h1": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": []}}
        mock_run = MagicMock(side_effect=self._mock_git(["h1"], shows))
        with patch("askr.session.checkpoint.subprocess.run", mock_run):
            checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
            key = ("dev", "/repo/askr_state")
            fetched_at, corpus = checkpoint._accomplished_corpus_cache[key]
            checkpoint._accomplished_corpus_cache[key] = (
                fetched_at - checkpoint._ACCOMPLISHED_CORPUS_TTL_SECS - 1, corpus,
            )
            calls_before_expiry_check = mock_run.call_count
            checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
        self.assertGreater(mock_run.call_count, calls_before_expiry_check)

    def test_different_state_dir_keys_do_not_share_cache(self):
        shows = {"h1": {"accomplishments": [{"what": "did thing A", "done": True}], "completed_goals": []}}
        mock_run = MagicMock(side_effect=self._mock_git(["h1"], shows))
        with patch("askr.session.checkpoint.subprocess.run", mock_run):
            checkpoint._load_accomplished_corpus("dev", "/repo/askr_state")
            calls_before = mock_run.call_count
            checkpoint._load_accomplished_corpus("dev", "/other_repo/askr_state")
        self.assertGreater(mock_run.call_count, calls_before)


# ---------------------------------------------------------------------------
# Wired into _run_light_handover (via create_checkpoint) — the filtered
# next_actions must be what reaches _generate_handover_with_llm, and a
# failure in the filter must leave existing_handover's next_actions untouched.
# ---------------------------------------------------------------------------

class NextActionFilterWiredIntoHandoverTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = os.path.join(self._tmp.name, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self.transcript_path = os.path.join(self._tmp.name, "t.jsonl")
        with open(self.transcript_path, "w") as f:
            f.write(json.dumps({"message": {"role": "user", "content": "hi"}}) + "\n")

    def tearDown(self):
        self._tmp.cleanup()

    def _base_patches(self, mock_llm_return):
        return [
            patch.object(checkpoint, "_generate_handover_with_llm", return_value=mock_llm_return),
            patch.object(checkpoint, "_generate_project_brief"),
            patch.object(checkpoint, "_regenerate_architecture_md"),
            patch.object(checkpoint, "_infer_and_queue_tasks"),
            patch.object(checkpoint, "git_commit_push", return_value=(True, "")),
            patch.object(checkpoint, "_notify_discord_checkpoint"),
            patch("askr.state.analytics.record_session_end", return_value=0),
        ]

    def test_matched_next_action_is_filtered_before_llm_call(self):
        existing = {
            "task": "prior work",
            "next_actions": [
                {"order": 1, "action": "Build structured JSONL event log for trigger and companion lineage"},
                {"order": 2, "action": "Build a visualization dashboard for the session event log"},
            ],
        }
        with patch("askr.state.reader.load_own_handover_raw", return_value=existing), \
             patch.object(checkpoint, "_load_accomplished_corpus",
                           return_value=["add structured JSONL event log for trigger companion lineage"]), \
             patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()) as mock_llm, \
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
        surviving = [a["action"] for a in kwargs["existing_handover"]["next_actions"]]
        self.assertEqual(surviving, ["Build a visualization dashboard for the session event log"])

    def test_corpus_load_failure_leaves_next_actions_untouched(self):
        existing = {
            "task": "prior work",
            "next_actions": [{"order": 1, "action": "Build a visualization dashboard"}],
        }
        with patch("askr.state.reader.load_own_handover_raw", return_value=existing), \
             patch.object(checkpoint, "_load_accomplished_corpus", side_effect=Exception("boom")), \
             patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()) as mock_llm, \
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
        self.assertEqual(kwargs["existing_handover"]["next_actions"], existing["next_actions"])

    def test_no_existing_next_actions_skips_filter_call_entirely(self):
        existing = {"task": "prior work", "next_actions": []}
        with patch("askr.state.reader.load_own_handover_raw", return_value=existing), \
             patch.object(checkpoint, "_load_accomplished_corpus") as mock_corpus, \
             patch.object(checkpoint, "_generate_handover_with_llm", return_value=_llm_summary()), \
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
        mock_corpus.assert_not_called()


if __name__ == "__main__":
    unittest.main()
