"""
Tests for lifecycle._watch_for_native_resume (2026-09-06), which replaces
the retired _watch_for_premature_activity / _alert_premature_activity pair.

Claude Code's CLI now natively handles the exhausted -> wait -> resume cycle
on its own for some sessions ("Usage limit reached ... continuing
automatically" -> "Usage limit reset ... continuing automatically"), but not
all — other sessions that hit the limit the same night sat frozen
indefinitely with nothing watching them. Sending Escape (the old mechanism)
actively cancels the native auto-continue rather than enabling it, so this
function never touches the terminal — it just waits past the real reset
plus a grace buffer and checks whether the transcript resumed writing on
its own, letting the caller decide whether a manual 'cont' is still needed.
"""

import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class WatchForNativeResumeTests(unittest.TestCase):
    def _iso(self, seconds_from_now):
        return (datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)).isoformat()

    def test_activity_detected_returns_true_immediately(self):
        """The mtime check runs before the target-time check, so a transcript
        that already resumed writing is detected as a native resume even if
        reset_at (and its grace window) is already in the past."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            baseline = os.path.getmtime(path)
            time.sleep(0.05)
            os.utime(path, None)  # bump mtime past baseline
            result = lifecycle._watch_for_native_resume(
                path, self._iso(-300), baseline, project_path="/proj", session_id="sess-1",
            )
            self.assertTrue(result)
        finally:
            os.remove(path)

    def test_no_activity_after_grace_window_returns_false(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            baseline = os.path.getmtime(f.name)
            # reset_at + _NATIVE_RESUME_GRACE_SECS is already fully in the
            # past -> exits "not resumed" on the very first check.
            result = lifecycle._watch_for_native_resume(f.name, self._iso(-300), baseline)
        self.assertFalse(result)

    def test_unparseable_reset_time_returns_false(self):
        result = lifecycle._watch_for_native_resume(
            "/some/transcript.jsonl", "not-a-real-timestamp", time.time(),
        )
        self.assertFalse(result)

    def test_missing_transcript_file_does_not_raise(self):
        try:
            result = lifecycle._watch_for_native_resume(
                "/definitely/does/not/exist.jsonl", self._iso(-300), time.time(),
            )
        except Exception as e:
            self.fail(f"_watch_for_native_resume raised: {e}")
        self.assertFalse(result)

    def test_polls_while_within_grace_window_before_concluding(self):
        """Not yet past target and no activity yet -> must actually loop
        (not conclude on the first check) — verified by shrinking the poll
        interval and grace window so the test stays fast."""
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            baseline = os.path.getmtime(path)
            from unittest.mock import patch
            with patch.object(lifecycle, "_NATIVE_RESUME_POLL_SECS", 0.02), \
                 patch.object(lifecycle, "_NATIVE_RESUME_GRACE_SECS", 0.06):
                result = lifecycle._watch_for_native_resume(path, self._iso(0), baseline)
            self.assertFalse(result)  # never bumped mtime -> still not resumed
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
