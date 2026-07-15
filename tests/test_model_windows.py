"""
Tests for askr/session/model_windows.py — the cache-backed replacement for
monitor.py's old hardcoded model->context-window dict (which had no
correction path and silently under-sized every model it didn't know about,
e.g. claude-sonnet-5's real 1M window read as the 200K default).

Read side (get_context_window) must be instant and offline — it's called
from hooks. Write side (ensure_cached) is daemon-only and makes a real
network call on a genuine miss, so every test here mocks
usage_api.fetch_model_context_window rather than touching the network.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import model_windows


class GetContextWindowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cache_path = os.path.join(self._tmp.name, "model_context_windows.json")
        self._patch = patch.object(model_windows, "_CACHE_PATH", self._cache_path)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_no_cache_file_falls_back_to_seed(self):
        # No cache written yet — _load_cache() falls back to the seed dict,
        # so a model known at seed time is still correct with zero network.
        self.assertEqual(model_windows.get_context_window("claude-sonnet-5"), 1_000_000)

    def test_unknown_model_returns_conservative_default(self):
        self.assertEqual(
            model_windows.get_context_window("claude-some-future-model"),
            model_windows.DEFAULT_CONTEXT_WINDOW,
        )

    def test_on_disk_cache_overrides_seed(self):
        with open(self._cache_path, "w") as f:
            json.dump({"claude-sonnet-5": 42}, f)
        # Real value, not the seed's 1_000_000 — proves the on-disk cache wins.
        self.assertEqual(model_windows.get_context_window("claude-sonnet-5"), 42)

    def test_corrupt_cache_file_falls_back_to_seed_not_crash(self):
        with open(self._cache_path, "w") as f:
            f.write("not valid json{{{")
        self.assertEqual(model_windows.get_context_window("claude-sonnet-5"), 1_000_000)


class EnsureCachedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._cache_path = os.path.join(self._tmp.name, "model_context_windows.json")
        self._patch = patch.object(model_windows, "_CACHE_PATH", self._cache_path)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_cache_hit_never_calls_the_network(self):
        # Seeded models are cache hits from the moment ensure_cached looks —
        # this is the "hot path stays offline" guarantee for known models.
        with patch("askr.session.usage_api.fetch_model_context_window") as mock_fetch:
            model_windows.ensure_cached("claude-sonnet-5")
            mock_fetch.assert_not_called()

    def test_genuine_miss_triggers_one_live_lookup_and_persists(self):
        with patch("askr.session.usage_api.fetch_model_context_window", return_value=555_000) as mock_fetch:
            model_windows.ensure_cached("claude-brand-new-model")
            mock_fetch.assert_called_once_with("claude-brand-new-model")

        # Persisted — a later get_context_window call (no mock needed) sees it.
        self.assertEqual(model_windows.get_context_window("claude-brand-new-model"), 555_000)

    def test_failed_lookup_does_not_poison_the_cache(self):
        with patch("askr.session.usage_api.fetch_model_context_window", return_value=None):
            model_windows.ensure_cached("claude-unreachable-model")

        # Still falls back to the default — nothing was written for this model,
        # so the next daemon cycle will retry rather than caching a bad value.
        self.assertEqual(
            model_windows.get_context_window("claude-unreachable-model"),
            model_windows.DEFAULT_CONTEXT_WINDOW,
        )

    def test_second_call_for_same_model_does_not_refetch(self):
        with patch("askr.session.usage_api.fetch_model_context_window", return_value=555_000) as mock_fetch:
            model_windows.ensure_cached("claude-brand-new-model")
            model_windows.ensure_cached("claude-brand-new-model")
            mock_fetch.assert_called_once()


if __name__ == "__main__":
    unittest.main()
