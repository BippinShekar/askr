"""
Tests for askr/state/behavior_prefs.py — Phase 3.9 Behavioral Preference
Persistence.

Covers the fenced askr:prefs CLAUDE.md read/write/remove logic, the pending-
candidate store, and the dedup/confidence-filter/delivery logic. The LLM
extraction itself lives in checkpoint.py and is covered separately in
tests/test_checkpoint_behavior_prefs.py — this module is deliberately
LLM-free, so nothing here mocks call_claude.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.state import behavior_prefs as bp


class _IsolatedPathsMixin:
    """Redirect GLOBAL_CLAUDE_MD, the pending store, and notification.json to
    a temp dir, and chdir into a temp project dir for the project-scope
    CLAUDE.md — mirrors test_claude_md_guard.py's chdir pattern."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = os.path.join(self._tmp.name, "project")
        os.makedirs(self.project_dir)
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

        self._global_md = os.path.join(self._tmp.name, "global_CLAUDE.md")
        self._pending_path = os.path.join(self._tmp.name, "behavior_pending.json")
        self._notif_path = os.path.join(self._tmp.name, "notification.json")

        self._patches = [
            patch.object(bp, "GLOBAL_CLAUDE_MD", self._global_md),
            patch.object(bp, "_PENDING_PATH", self._pending_path),
            patch.object(bp, "NOTIFICATION_PATH", self._notif_path),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self):
        for p in self._patches:
            p.stop()
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _project_claude_md_path(self):
        return os.path.join(self.project_dir, "CLAUDE.md")


class ReadPersistedRulesTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(bp.read_persisted_rules("project"), [])
        self.assertEqual(bp.read_persisted_rules("global"), [])

    def test_reads_bullets_from_fenced_section(self):
        content = (
            f"{bp._PREFS_MARKER_START}\n"
            "## Askr — Detected Preferences\n\n"
            "- Always build in stages\n"
            "- Never use emojis\n"
            f"{bp._PREFS_MARKER_END}\n"
        )
        with open(self._project_claude_md_path(), "w") as f:
            f.write(content)
        self.assertEqual(
            bp.read_persisted_rules("project"),
            ["Always build in stages", "Never use emojis"],
        )

    def test_ignores_content_outside_fenced_section(self):
        content = "# My notes\n\n- not a persisted rule\n"
        with open(self._project_claude_md_path(), "w") as f:
            f.write(content)
        self.assertEqual(bp.read_persisted_rules("project"), [])

    def test_read_all_persisted_rules_splits_by_scope(self):
        bp.write_rule("Always build in stages", "global")
        bp.write_rule("Use unittest.TestCase for tests", "project")
        rules = bp.read_all_persisted_rules()
        self.assertEqual(rules["global"], ["Always build in stages"])
        self.assertEqual(rules["project"], ["Use unittest.TestCase for tests"])


class WriteRuleTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_creates_file_and_section_when_missing(self):
        result = bp.write_rule("Always build in stages", "project")
        self.assertTrue(result)
        content = open(self._project_claude_md_path()).read()
        self.assertIn(bp._PREFS_MARKER_START, content)
        self.assertIn("Always build in stages", content)

    def test_appends_to_existing_section(self):
        bp.write_rule("Always build in stages", "project")
        bp.write_rule("Never use emojis", "project")
        rules = bp.read_persisted_rules("project")
        self.assertEqual(rules, ["Always build in stages", "Never use emojis"])

    def test_duplicate_rule_is_a_noop(self):
        self.assertTrue(bp.write_rule("Always build in stages", "project"))
        self.assertFalse(bp.write_rule("Always build in stages", "project"))
        self.assertEqual(bp.read_persisted_rules("project"), ["Always build in stages"])

    def test_near_duplicate_rule_is_a_noop(self):
        bp.write_rule("Always build in stages.", "project")
        self.assertFalse(bp.write_rule("always build in stages", "project"))
        self.assertEqual(len(bp.read_persisted_rules("project")), 1)

    def test_preserves_content_outside_fenced_section(self):
        with open(self._project_claude_md_path(), "w") as f:
            f.write("# My Project\n\nHand-written notes.\n")
        bp.write_rule("Always build in stages", "project")
        content = open(self._project_claude_md_path()).read()
        self.assertIn("Hand-written notes.", content)
        self.assertIn("Always build in stages", content)

    def test_global_and_project_scopes_are_independent(self):
        bp.write_rule("Global rule", "global")
        self.assertEqual(bp.read_persisted_rules("project"), [])
        self.assertEqual(bp.read_persisted_rules("global"), ["Global rule"])

    def test_empty_rule_is_a_noop(self):
        self.assertFalse(bp.write_rule("   ", "project"))
        self.assertFalse(os.path.exists(self._project_claude_md_path()))


class RemoveRuleTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_removes_from_project_scope(self):
        bp.write_rule("Always build in stages", "project")
        scope = bp.remove_rule("Always build in stages")
        self.assertEqual(scope, "project")
        self.assertEqual(bp.read_persisted_rules("project"), [])

    def test_removes_from_global_scope_when_not_in_project(self):
        bp.write_rule("Always build in stages", "global")
        scope = bp.remove_rule("Always build in stages")
        self.assertEqual(scope, "global")
        self.assertEqual(bp.read_persisted_rules("global"), [])

    def test_project_scope_checked_before_global(self):
        bp.write_rule("Same rule text", "project")
        bp.write_rule("Same rule text", "global")
        scope = bp.remove_rule("Same rule text")
        self.assertEqual(scope, "project")
        # global copy untouched
        self.assertEqual(bp.read_persisted_rules("global"), ["Same rule text"])

    def test_not_found_returns_empty_string(self):
        self.assertEqual(bp.remove_rule("Never persisted"), "")

    def test_removing_last_rule_cleans_up_section(self):
        bp.write_rule("Only rule", "project")
        bp.remove_rule("Only rule")
        content = open(self._project_claude_md_path()).read()
        self.assertNotIn(bp._PREFS_MARKER_START, content)

    def test_removing_one_of_several_keeps_others(self):
        bp.write_rule("Rule one", "project")
        bp.write_rule("Rule two", "project")
        bp.remove_rule("Rule one")
        self.assertEqual(bp.read_persisted_rules("project"), ["Rule two"])


class PendingStoreTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_load_pending_empty_when_missing(self):
        self.assertEqual(bp.load_pending(), [])

    def test_add_pending_persists_entries(self):
        added = bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        self.assertEqual(len(added), 1)
        pending = bp.load_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["rule"], "Always build in stages")
        self.assertEqual(pending[0]["scope"], "global")

    def test_add_pending_dedupes_against_existing_pending(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        added = bp.add_pending([{"rule": "Always build in stages", "confidence": 0.95, "scope": "global"}])
        self.assertEqual(added, [])
        self.assertEqual(len(bp.load_pending()), 1)

    def test_add_pending_defaults_scope_to_project(self):
        bp.add_pending([{"rule": "No scope given", "confidence": 0.9}])
        self.assertEqual(bp.load_pending()[0]["scope"], "project")

    def test_remove_pending_removes_matching_entry(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        self.assertTrue(bp.remove_pending("Always build in stages"))
        self.assertEqual(bp.load_pending(), [])

    def test_remove_pending_returns_false_when_not_found(self):
        self.assertFalse(bp.remove_pending("Nothing here"))

    def test_corrupt_pending_file_fails_open(self):
        os.makedirs(os.path.dirname(self._pending_path), exist_ok=True)
        with open(self._pending_path, "w") as f:
            f.write("not valid json{{{")
        self.assertEqual(bp.load_pending(), [])


class DedupCandidatesTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_filters_out_already_persisted(self):
        bp.write_rule("Always build in stages", "project")
        candidates = [{"rule": "Always build in stages", "confidence": 0.9, "scope": "project"}]
        self.assertEqual(bp.dedup_candidates(candidates), [])

    def test_filters_out_already_pending(self):
        bp.add_pending([{"rule": "Never use emojis", "confidence": 0.9, "scope": "global"}])
        candidates = [{"rule": "Never use emojis", "confidence": 0.9, "scope": "global"}]
        self.assertEqual(bp.dedup_candidates(candidates), [])

    def test_keeps_genuinely_new_candidates(self):
        candidates = [{"rule": "Commit clean, no AI co-author", "confidence": 0.9, "scope": "global"}]
        self.assertEqual(bp.dedup_candidates(candidates), candidates)

    def test_mixed_batch_keeps_only_new(self):
        bp.write_rule("Always build in stages", "project")
        candidates = [
            {"rule": "Always build in stages", "confidence": 0.9, "scope": "project"},
            {"rule": "Commit clean, no AI co-author", "confidence": 0.9, "scope": "global"},
        ]
        result = bp.dedup_candidates(candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["rule"], "Commit clean, no AI co-author")


class FilterHighConfidenceTests(unittest.TestCase):
    def test_keeps_only_at_or_above_threshold(self):
        candidates = [
            {"rule": "A", "confidence": 0.9},
            {"rule": "B", "confidence": 0.5},
            {"rule": "C", "confidence": bp.CONFIDENCE_THRESHOLD},
        ]
        result = bp.filter_high_confidence(candidates)
        rules = {c["rule"] for c in result}
        self.assertEqual(rules, {"A", "C"})

    def test_missing_or_invalid_confidence_treated_as_zero(self):
        candidates = [{"rule": "A"}, {"rule": "B", "confidence": "not-a-number"}]
        self.assertEqual(bp.filter_high_confidence(candidates), [])


class DeliverCandidatesTests(_IsolatedPathsMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._spawn_patch = patch.object(bp, "_spawn_fallback_worker")
        self._mock_spawn = self._spawn_patch.start()

    def tearDown(self):
        self._spawn_patch.stop()
        super().tearDown()

    def test_writes_notification_and_spawns_fallback(self):
        candidates = [{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}]
        result = bp.deliver_candidates(candidates, project_path=self.project_dir)
        self.assertTrue(result)

        with open(self._notif_path) as f:
            n = json.load(f)
        self.assertEqual(n["type"], "behavior_confirm")
        self.assertEqual(n["shown"], False)
        self.assertEqual(len(n["rules"]), 1)
        self.assertEqual(n["rules"][0]["rule"], "Always build in stages")

        self._mock_spawn.assert_called_once()

    def test_adds_to_pending_store(self):
        candidates = [{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}]
        bp.deliver_candidates(candidates, project_path=self.project_dir)
        pending = bp.load_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["rule"], "Always build in stages")

    def test_all_candidates_already_pending_is_a_noop(self):
        candidates = [{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}]
        bp.deliver_candidates(candidates, project_path=self.project_dir)
        self._mock_spawn.reset_mock()

        result = bp.deliver_candidates(candidates, project_path=self.project_dir)
        self.assertFalse(result)
        self._mock_spawn.assert_not_called()


class HeadlessPersistTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_writes_rule_and_notifies_discord(self):
        with patch("askr.clients.discord.send_message") as mock_send:
            mock_send.return_value = (True, "")
            persisted = bp._headless_persist(
                [{"rule": "Always build in stages", "scope": "global"}],
                project_path=self.project_dir,
            )
        self.assertEqual(persisted, ["Always build in stages"])
        self.assertEqual(bp.read_persisted_rules("global"), ["Always build in stages"])
        mock_send.assert_called_once()
        message = mock_send.call_args[0][0]
        self.assertIn("Detected and persisted", message)
        self.assertIn("askr prefs remove", message)

    def test_removes_from_pending_after_persisting(self):
        bp.add_pending([{"rule": "Always build in stages", "confidence": 0.9, "scope": "global"}])
        with patch("askr.clients.discord.send_message", return_value=(True, "")):
            bp._headless_persist(
                [{"rule": "Always build in stages", "scope": "global"}],
                project_path=self.project_dir,
            )
        self.assertEqual(bp.load_pending(), [])

    def test_no_discord_call_when_nothing_new_persisted(self):
        bp.write_rule("Always build in stages", "global")
        with patch("askr.clients.discord.send_message") as mock_send:
            persisted = bp._headless_persist(
                [{"rule": "Always build in stages", "scope": "global"}],
                project_path=self.project_dir,
            )
        self.assertEqual(persisted, [])
        mock_send.assert_not_called()


class FallbackWorkerTests(_IsolatedPathsMixin, unittest.TestCase):
    def test_skips_when_notification_already_shown(self):
        with open(self._notif_path, "w") as f:
            json.dump({"type": "behavior_confirm", "shown": True, "rules": []}, f)
        with patch.object(bp, "_headless_persist") as mock_persist:
            bp._fallback_worker(self.project_dir, delay=0)
        mock_persist.assert_not_called()

    def test_persists_when_notification_never_claimed(self):
        rules = [{"rule": "Always build in stages", "scope": "global"}]
        with open(self._notif_path, "w") as f:
            json.dump({"type": "behavior_confirm", "shown": False, "rules": rules}, f)
        with patch.object(bp, "_headless_persist") as mock_persist:
            bp._fallback_worker(self.project_dir, delay=0)
        mock_persist.assert_called_once_with(rules, self.project_dir)

    def test_skips_when_notification_overwritten_by_different_type(self):
        with open(self._notif_path, "w") as f:
            json.dump({"type": "context", "shown": False}, f)
        with patch.object(bp, "_headless_persist") as mock_persist:
            bp._fallback_worker(self.project_dir, delay=0)
        mock_persist.assert_not_called()

    def test_missing_notification_file_is_a_noop(self):
        with patch.object(bp, "_headless_persist") as mock_persist:
            bp._fallback_worker(self.project_dir, delay=0)
        mock_persist.assert_not_called()


if __name__ == "__main__":
    unittest.main()
