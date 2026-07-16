"""
Tests for Phase 3.15 (Smart Context Injection) — askr/state/reader.py.

Covers: targeted injection driven by files_in_play/relational_files (S1),
snapshot-sourced file purposes with graceful degradation (S2), TF-IDF
decision relevance (S3), rejected-decisions domain filter (S4), failed-
approaches relevance + recency floor (S5), the token budget cap (S6), and
the full-dump fallback when there's no targeting signal yet (S7).
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import reader


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


class ReaderTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.state_dir = self._tmp.name
        self._patch = patch("askr.state.reader.state_path",
                             side_effect=lambda name: os.path.join(self.state_dir, name))
        self._patch.start()
        # Isolate the Phase 3.14 snapshot lookup too — without this it falls
        # through to the real project's own .llm_snapshot/summary.json (found
        # via get_state_dir()'s cwd-relative project-root walk, since tests
        # run from the repo root), leaking real snapshot content into what's
        # supposed to be an empty/isolated fixture.
        self._snap_dir = os.path.join(self.state_dir, "_no_snapshot")
        self._snapshot_patch = patch("askr.state.reader.snapshot_path",
                                      side_effect=lambda name: os.path.join(self._snap_dir, name))
        self._snapshot_patch.start()

    def tearDown(self):
        self._patch.stop()
        self._snapshot_patch.stop()
        self._tmp.cleanup()

    def _own_handover(self, **overrides):
        data = {"task": "", "next_actions": [], "files_in_play": [], "relational_files": []}
        data.update(overrides)
        _write_json(os.path.join(self.state_dir, "handover_dev.json"), data)


class FallbackModeTests(ReaderTestBase):
    """S7: no files_in_play/relational_files signal — full-dump behavior preserved."""

    def test_no_handover_returns_empty(self):
        with patch("askr.state.config.load_developer", return_value="dev"):
            self.assertEqual(reader.build_context_injection("dev"), "")

    def test_empty_files_in_play_falls_back_to_full_dump(self):
        self._own_handover(task="do a thing")
        with open(os.path.join(self.state_dir, "decisions.jsonl"), "w") as f:
            f.write(json.dumps({"at": "t1", "dev": "dev", "decision": "use X", "reason": "because"}) + "\n")
        with open(os.path.join(self.state_dir, "architecture.md"), "w") as f:
            f.write("# Architecture\nSome content.")

        result = reader.build_context_injection("dev")
        self.assertIn("RECENT DECISIONS", result)
        self.assertIn("ARCHITECTURE", result)
        # Fallback path must NOT include the targeted-mode-only section label.
        self.assertNotIn("RELEVANT FILES", result)

    def test_str_only_handover_md_falls_back(self):
        # Legacy .md-only handover (no JSON) — load_own_handover_raw returns a str.
        with open(os.path.join(self.state_dir, "handover_dev.md"), "w") as f:
            f.write("# Handover\nSome legacy content.")
        result = reader.build_context_injection("dev")
        self.assertIn("Some legacy content", result)


class TargetedModeTests(ReaderTestBase):
    """S1/S2: files_in_play/relational_files drive what gets pulled in."""

    def test_files_in_play_produces_relevant_files_section(self):
        self._own_handover(
            task="fix the auth bug",
            files_in_play=["askr/auth.py"],
            relational_files=[{"file": "askr/middleware.py", "relationship": "imports", "why": "shared session logic"}],
        )
        result = reader.build_context_injection("dev")
        self.assertIn("RELEVANT FILES", result)
        self.assertIn("askr/auth.py", result)
        self.assertIn("askr/middleware.py", result)
        self.assertIn("shared session logic", result)

    def test_snapshot_purpose_is_pulled_in_when_available(self):
        self._own_handover(files_in_play=["askr/auth.py"])
        snapshot_dir = os.path.join(self.state_dir, "..", "snapshot")
        os.makedirs(snapshot_dir, exist_ok=True)
        snapshot_file = os.path.join(snapshot_dir, "summary.json")
        with open(snapshot_file, "w") as f:
            json.dump([{"file": "askr/auth.py", "purpose": "handles OAuth token refresh"}], f)

        # snapshot_path() (askr/state/reader.py) is the real seam now — it's
        # project-root-anchored via get_state_dir(), not the bare cwd-relative
        # SNAPSHOT_DIR constant this test used to patch directly.
        with patch("askr.state.reader.snapshot_path",
                    side_effect=lambda name: os.path.join(snapshot_dir, name)):
            result = reader.build_context_injection("dev")
        self.assertIn("handles OAuth token refresh", result)

    def test_missing_snapshot_degrades_to_bare_path(self):
        self._own_handover(files_in_play=["askr/auth.py"])
        with patch("askr.state.reader.snapshot_path",
                    side_effect=lambda name: os.path.join("/no/such/dir", name)):
            result = reader.build_context_injection("dev")
        self.assertIn("askr/auth.py", result)


class RelevantDecisionsTests(ReaderTestBase):
    """S3: TF-IDF relevance ranking, not just recency."""

    def test_relevant_old_decision_outranks_irrelevant_recent_one(self):
        with open(os.path.join(self.state_dir, "decisions.jsonl"), "w") as f:
            f.write(json.dumps({"at": "t1", "dev": "dev", "decision": "OAuth tokens refresh via middleware.py"}) + "\n")
            for i in range(15):
                f.write(json.dumps({"at": f"t{i+2}", "dev": "dev", "decision": f"unrelated cleanup {i}"}) + "\n")

        result = reader.load_relevant_decisions("fix the oauth middleware token refresh bug", top_n=3)
        self.assertIn("OAuth tokens refresh via middleware.py", result)

    def test_no_query_falls_back_to_recency(self):
        with open(os.path.join(self.state_dir, "decisions.jsonl"), "w") as f:
            for i in range(5):
                f.write(json.dumps({"at": f"t{i}", "dev": "dev", "decision": f"decision {i}"}) + "\n")
        result = reader.load_relevant_decisions("", top_n=2)
        self.assertIn("decision 4", result)
        self.assertIn("decision 3", result)

    def test_missing_file_returns_empty(self):
        self.assertEqual(reader.load_relevant_decisions("anything"), "")


class RejectedDecisionsFilterTests(ReaderTestBase):
    """S4: rejected decisions filtered by domain matching in-play/relational files."""

    def test_matching_domain_is_surfaced(self):
        with open(os.path.join(self.state_dir, "rejected_decisions.jsonl"), "w") as f:
            f.write(json.dumps({
                "what_was_proposed": "use a global mutable cache",
                "domain": "askr/session/lifecycle.py",
                "confidence": 0.9,
            }) + "\n")
        result = reader._format_rejected_decisions(["askr/session/lifecycle.py"], [])
        self.assertIn("global mutable cache", result)

    def test_non_matching_domain_is_excluded(self):
        with open(os.path.join(self.state_dir, "rejected_decisions.jsonl"), "w") as f:
            f.write(json.dumps({
                "what_was_proposed": "rewrite the CLI in Go",
                "domain": "askr/cli/askr.py",
                "confidence": 0.9,
            }) + "\n")
        result = reader._format_rejected_decisions(["askr/session/lifecycle.py"], [])
        self.assertEqual(result, "")

    def test_missing_file_never_errors(self):
        result = reader._format_rejected_decisions(["anything.py"], [])
        self.assertEqual(result, "")

    def test_empty_scope_returns_empty(self):
        with open(os.path.join(self.state_dir, "rejected_decisions.jsonl"), "w") as f:
            f.write(json.dumps({"what_was_proposed": "x", "domain": "y.py"}) + "\n")
        result = reader._format_rejected_decisions([], [])
        self.assertEqual(result, "")


class FailedApproachesTests(ReaderTestBase):
    """S5: never wired into injection before — now relevance + recency floor."""

    def test_recent_items_always_included(self):
        with open(os.path.join(self.state_dir, "failed_approaches.md"), "w") as f:
            for i in range(10):
                f.write(f"- attempt {i}: totally unrelated topic\n")
        result = reader._format_failed_approaches("nothing matches this")
        # Recency floor = last 3, regardless of relevance score.
        self.assertIn("attempt 9", result)
        self.assertIn("attempt 8", result)
        self.assertIn("attempt 7", result)

    def test_relevant_old_item_surfaced_even_if_not_recent(self):
        with open(os.path.join(self.state_dir, "failed_approaches.md"), "w") as f:
            f.write("- tried a global mutable cache for session state: caused race conditions\n")
            for i in range(10):
                f.write(f"- unrelated attempt {i}\n")
        result = reader._format_failed_approaches("session state cache race condition")
        self.assertIn("global mutable cache", result)

    def test_no_failed_approaches_returns_empty(self):
        self.assertEqual(reader._format_failed_approaches("anything"), "")


class ContextBudgetTests(unittest.TestCase):
    """S6: lower-priority sections drop first when the budget is exceeded."""

    def test_under_budget_keeps_everything(self):
        always = ["short always section"]
        prioritized = [("a", "short a"), ("b", "short b")]
        result = reader._apply_budget(always, prioritized)
        self.assertEqual(result, ["short always section", "short a", "short b"])

    def test_over_budget_drops_lowest_priority_first(self):
        always = ["x" * 100]
        huge = "y" * (reader._CONTEXT_BUDGET_TOKENS * 4)  # far over budget alone
        prioritized = [("high_priority", "small high-priority text"), ("low_priority", huge)]
        result = reader._apply_budget(always, prioritized)
        self.assertIn("small high-priority text", result)
        self.assertNotIn(huge, result)

    def test_empty_prioritized_text_is_skipped(self):
        result = reader._apply_budget(["always"], [("a", ""), ("b", None)])
        self.assertEqual(result, ["always"])


class TfidfRankTests(unittest.TestCase):
    def test_empty_documents_returns_empty(self):
        self.assertEqual(reader._tfidf_rank("query", [], 5), [])

    def test_top_n_respected(self):
        docs = [f"doc about topic {i}" for i in range(20)]
        result = reader._tfidf_rank("topic", docs, 5)
        self.assertLessEqual(len(result), 5)


if __name__ == "__main__":
    unittest.main()
