"""
Tests for the independent quota poll (2026-08-12) — the fix for the actual
root cause of "the 90% hard stop doesn't work."

Confirmed live: a session's per-project stats file froze at 84.0% — bit-for-
bit identical across every 15s daemon poll for 5+ minutes straight — while
the real account kept climbing past 90% and blocked entirely. quota_pct only
refreshes via PostToolUse, which needs a SUCCESSFUL tool call; once the
account is genuinely exhausted, no more successful calls happen to refresh
it, so the file just stops updating at whatever it last recorded, forever
below QUOTA_TRIGGER as far as the per-project check can tell.

_poll_independent_quota_and_fire runs on every daemon loop iteration,
independent of _session_is_active() and any single stats file's freshness,
polling the true account-wide quota directly. _read_stale_high_quota_stats
is the complementary read that finds WHICH project to act on even when its
own stats file has gone stale precisely because it's the one that's blocked.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class ReadStaleHighQuotaStatsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_stats_dir = lifecycle._STATS_DIR
        lifecycle._STATS_DIR = self._tmp.name

    def tearDown(self):
        lifecycle._STATS_DIR = self._orig_stats_dir
        self._tmp.cleanup()

    def _write_stats(self, name, quota_pct, age_secs):
        path = os.path.join(self._tmp.name, name)
        with open(path, "w") as f:
            json.dump({"project_path": f"/fake/{name}", "session_id": name, "quota_pct": quota_pct}, f)
        mtime = time.time() - age_secs
        os.utime(path, (mtime, mtime))

    def test_fresh_file_excluded_already_covered_by_read_all_stats(self):
        self._write_stats("a.json", 95.0, age_secs=60)  # well within SESSION_STALE_SECS
        self.assertEqual(lifecycle._read_stale_high_quota_stats(), [])

    def test_stale_with_high_quota_is_included(self):
        self._write_stats("a.json", 84.0, age_secs=lifecycle.SESSION_STALE_SECS + 60)
        results = lifecycle._read_stale_high_quota_stats()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["quota_pct"], 84.0)

    def test_stale_with_low_quota_is_excluded(self):
        self._write_stats("a.json", 40.0, age_secs=lifecycle.SESSION_STALE_SECS + 60)
        self.assertEqual(lifecycle._read_stale_high_quota_stats(), [])

    def test_too_old_is_excluded_even_with_high_quota(self):
        self._write_stats("a.json", 95.0, age_secs=lifecycle._STALE_HIGH_QUOTA_MAX_AGE_SECS + 60)
        self.assertEqual(lifecycle._read_stale_high_quota_stats(), [])

    def test_exactly_at_threshold_is_included(self):
        self._write_stats("a.json", lifecycle._STALE_HIGH_QUOTA_THRESHOLD,
                          age_secs=lifecycle.SESSION_STALE_SECS + 60)
        self.assertEqual(len(lifecycle._read_stale_high_quota_stats()), 1)

    def test_malformed_json_skipped_not_raised(self):
        path = os.path.join(self._tmp.name, "bad.json")
        with open(path, "w") as f:
            f.write("not json")
        mtime = time.time() - (lifecycle.SESSION_STALE_SECS + 60)
        os.utime(path, (mtime, mtime))
        try:
            result = lifecycle._read_stale_high_quota_stats()
        except Exception as e:
            self.fail(f"_read_stale_high_quota_stats raised: {e}")
        self.assertEqual(result, [])

    def test_missing_stats_dir_returns_empty(self):
        lifecycle._STATS_DIR = "/definitely/does/not/exist"
        self.assertEqual(lifecycle._read_stale_high_quota_stats(), [])

    def test_multiple_stale_high_quota_files_all_included(self):
        self._write_stats("a.json", 84.0, age_secs=lifecycle.SESSION_STALE_SECS + 60)
        self._write_stats("b.json", 91.0, age_secs=lifecycle.SESSION_STALE_SECS + 120)
        results = lifecycle._read_stale_high_quota_stats()
        self.assertEqual(len(results), 2)


class PollIndependentQuotaAndFireTests(unittest.TestCase):
    def setUp(self):
        patches = [
            patch.object(lifecycle, "_log"),
            patch.object(lifecycle, "_save_quota_triggered_windows"),
            patch("askr.state.writer.append_event"),
        ]
        self._mocks = {p.attribute: p.start() for p in patches}
        self.addCleanup(lambda: [p.stop() for p in patches])

        thread_patch = patch.object(lifecycle.threading, "Thread")
        self.mock_thread_cls = thread_patch.start()
        self.addCleanup(thread_patch.stop)
        self.mock_thread = MagicMock()
        self.mock_thread_cls.return_value = self.mock_thread

    def _thread_targets_and_args(self):
        return [(c.kwargs.get("target"), c.kwargs.get("args")) for c in self.mock_thread_cls.call_args_list]

    def _status(self, pct, reset_iso="2026-08-12T20:00:00+00:00"):
        return MagicMock(
            five_hour_pct=pct,
            five_hour_reset=datetime.fromisoformat(reset_iso),
        )

    def test_throttled_within_poll_interval_does_not_call_api(self):
        last_poll = time.time()
        with patch("askr.session.usage_api.get_quota_status") as mock_status:
            result = lifecycle._poll_independent_quota_and_fire(last_poll, set(), {})
        mock_status.assert_not_called()
        self.assertEqual(result, last_poll)  # throttled — timestamp unchanged

    def test_api_returns_none_advances_timestamp_no_fire(self):
        with patch("askr.session.usage_api.get_quota_status", return_value=None):
            result = lifecycle._poll_independent_quota_and_fire(0.0, set(), {})
        self.assertGreater(result, 0.0)
        self.mock_thread_cls.assert_not_called()

    def test_below_trigger_threshold_no_fire(self):
        with patch("askr.session.usage_api.get_quota_status", return_value=self._status(89.9)):
            lifecycle._poll_independent_quota_and_fire(0.0, set(), {})
        self.mock_thread_cls.assert_not_called()

    def test_already_triggered_window_within_tolerance_no_fire(self):
        stored = {"2026-08-12T19:59:55+00:00"}  # 5s off — within tolerance
        with patch("askr.session.usage_api.get_quota_status",
                   return_value=self._status(95.0, "2026-08-12T20:00:00+00:00")):
            lifecycle._poll_independent_quota_and_fire(0.0, stored, {})
        self.mock_thread_cls.assert_not_called()

    def test_fires_for_project_from_read_all_stats(self):
        stats = {"project_path": "/fake/proj", "session_id": "sess1", "quota_pct": 91.0}
        with patch("askr.session.usage_api.get_quota_status", return_value=self._status(95.0)), \
             patch.object(lifecycle, "_read_all_stats", return_value=[stats]), \
             patch.object(lifecycle, "_read_stale_high_quota_stats", return_value=[]):
            lifecycle._poll_independent_quota_and_fire(0.0, set(), {})

        targets = self._thread_targets_and_args()
        self.assertEqual(len(targets), 1)
        target, args = targets[0]
        self.assertEqual(target, lifecycle._execute_quota_trigger)
        fresh_stats, project_path, session_id = args
        self.assertEqual(project_path, "/fake/proj")
        self.assertEqual(session_id, "sess1")
        # The fresh live percentage must be threaded through, not the stale one.
        self.assertEqual(fresh_stats["quota_pct"], 95.0)

    def test_fires_for_project_only_from_stale_high_quota_stats(self):
        """The exact scenario confirmed live: the project's OWN stats file
        has gone stale (excluded from _read_all_stats), but its last-known
        high reading makes it a candidate via the stale-but-was-high read."""
        stale_stats = {"project_path": "/fake/frozen-proj", "session_id": "sess2", "quota_pct": 84.0}
        with patch("askr.session.usage_api.get_quota_status", return_value=self._status(100.0)), \
             patch.object(lifecycle, "_read_all_stats", return_value=[]), \
             patch.object(lifecycle, "_read_stale_high_quota_stats", return_value=[stale_stats]):
            lifecycle._poll_independent_quota_and_fire(0.0, set(), {})

        targets = self._thread_targets_and_args()
        self.assertEqual(len(targets), 1)
        _, args = targets[0]
        self.assertEqual(args[1], "/fake/frozen-proj")

    def test_dedupes_by_project_path_across_both_sources(self):
        same_project_fresh = {"project_path": "/fake/proj", "session_id": "sess-fresh", "quota_pct": 91.0}
        same_project_stale = {"project_path": "/fake/proj", "session_id": "sess-stale", "quota_pct": 84.0}
        with patch("askr.session.usage_api.get_quota_status", return_value=self._status(95.0)), \
             patch.object(lifecycle, "_read_all_stats", return_value=[same_project_fresh]), \
             patch.object(lifecycle, "_read_stale_high_quota_stats", return_value=[same_project_stale]):
            lifecycle._poll_independent_quota_and_fire(0.0, set(), {})

        targets = self._thread_targets_and_args()
        self.assertEqual(len(targets), 1)  # only one thread per unique project

    def test_no_candidates_still_advances_timestamp_but_does_not_mark_window(self):
        with patch("askr.session.usage_api.get_quota_status", return_value=self._status(95.0)), \
             patch.object(lifecycle, "_read_all_stats", return_value=[]), \
             patch.object(lifecycle, "_read_stale_high_quota_stats", return_value=[]):
            result = lifecycle._poll_independent_quota_and_fire(0.0, set(), {})
        self.assertGreater(result, 0.0)
        self.mock_thread_cls.assert_not_called()
        self._mocks["_save_quota_triggered_windows"].assert_not_called()

    def test_api_exception_fails_open_no_fire(self):
        with patch("askr.session.usage_api.get_quota_status", side_effect=Exception("boom")):
            try:
                result = lifecycle._poll_independent_quota_and_fire(0.0, set(), {})
            except Exception as e:
                self.fail(f"_poll_independent_quota_and_fire raised: {e}")
        self.mock_thread_cls.assert_not_called()


if __name__ == "__main__":
    unittest.main()
