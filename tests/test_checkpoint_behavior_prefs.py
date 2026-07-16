"""
Tests for checkpoint.py's _write_behavioral_preferences_from_handover — the
per-turn wiring that reads the behavioral_preferences field a handover LLM
response can carry (see _generate_handover_with_llm's schema) and hands
surfaced candidates off to behavior_prefs.deliver_candidates.

These mock behavior_prefs's filter/dedup/deliver functions rather than
exercising real file I/O — that logic is covered directly in
tests/test_behavior_prefs.py. This file verifies checkpoint.py's own
cleaning step (short/empty rule filtering, scope defaulting, confidence
coercion) and that it wires the three calls together correctly.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session.checkpoint import _write_behavioral_preferences_from_handover


class WriteBehavioralPreferencesFromHandoverTests(unittest.TestCase):
    def setUp(self):
        self.state_dir = "/tmp/does-not-matter"
        self.developer = "bippin"
        self.project_path = "/tmp/project"

    def test_none_handover_is_a_noop(self):
        with patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(None, self.state_dir, self.developer, self.project_path)
        mock_deliver.assert_not_called()

    def test_string_handover_is_a_noop(self):
        with patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover("not a dict", self.state_dir, self.developer, self.project_path)
        mock_deliver.assert_not_called()

    def test_no_behavioral_preferences_key_is_a_noop(self):
        handover = {"task": "did stuff"}
        with patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        mock_deliver.assert_not_called()

    def test_empty_behavioral_preferences_list_is_a_noop(self):
        handover = {"behavioral_preferences": []}
        with patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        mock_deliver.assert_not_called()

    def test_surfaced_candidate_is_delivered(self):
        handover = {"behavioral_preferences": [
            {"rule": "Always build in stages", "confidence": 0.95, "scope": "global"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c) as mock_filter, \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c) as mock_dedup, \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)

        mock_filter.assert_called_once()
        mock_dedup.assert_called_once()
        mock_deliver.assert_called_once()
        delivered = mock_deliver.call_args[0][0]
        self.assertEqual(delivered[0]["rule"], "Always build in stages")
        self.assertEqual(delivered[0]["scope"], "global")
        self.assertEqual(delivered[0]["confidence"], 0.95)
        self.assertEqual(mock_deliver.call_args[0][1], self.project_path)

    def test_dedup_returning_empty_skips_delivery(self):
        handover = {"behavioral_preferences": [
            {"rule": "Already persisted rule text", "confidence": 0.95, "scope": "global"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c), \
             patch("askr.state.behavior_prefs.dedup_candidates", return_value=[]), \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        mock_deliver.assert_not_called()

    def test_low_confidence_filtered_before_delivery(self):
        handover = {"behavioral_preferences": [
            {"rule": "Vague one-off remark", "confidence": 0.4, "scope": "project"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", return_value=[]) as mock_filter, \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c) as mock_dedup, \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        mock_filter.assert_called_once()
        # dedup still runs on the (now empty) filtered list — harmless no-op —
        # but nothing reaches delivery since there's nothing left to surface.
        mock_deliver.assert_not_called()

    def test_short_rule_text_is_dropped_before_filtering(self):
        handover = {"behavioral_preferences": [
            {"rule": "no", "confidence": 0.99, "scope": "global"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c) as mock_filter, \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c), \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        # "no" is < 8 chars — cleaned list passed to filter_high_confidence should be empty
        mock_filter.assert_called_once_with([])
        mock_deliver.assert_not_called()

    def test_invalid_scope_defaults_to_project(self):
        handover = {"behavioral_preferences": [
            {"rule": "Some clearly stated standing rule", "confidence": 0.95, "scope": "nonsense"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c), \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c), \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        delivered = mock_deliver.call_args[0][0]
        self.assertEqual(delivered[0]["scope"], "project")

    def test_invalid_confidence_coerced_to_zero(self):
        handover = {"behavioral_preferences": [
            {"rule": "Some clearly stated standing rule", "confidence": "not-a-number", "scope": "global"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c), \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c), \
             patch("askr.state.behavior_prefs.deliver_candidates") as mock_deliver:
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)
        delivered = mock_deliver.call_args[0][0]
        self.assertEqual(delivered[0]["confidence"], 0.0)

    def test_deliver_exception_is_swallowed(self):
        handover = {"behavioral_preferences": [
            {"rule": "Some clearly stated standing rule", "confidence": 0.95, "scope": "global"},
        ]}
        with patch("askr.state.behavior_prefs.filter_high_confidence", side_effect=lambda c, **k: c), \
             patch("askr.state.behavior_prefs.dedup_candidates", side_effect=lambda c, p: c), \
             patch("askr.state.behavior_prefs.deliver_candidates", side_effect=RuntimeError("boom")):
            # Must not raise — same fail-safe contract as the other
            # _write_*_from_handover helpers in checkpoint.py.
            _write_behavioral_preferences_from_handover(handover, self.state_dir, self.developer, self.project_path)


if __name__ == "__main__":
    unittest.main()
