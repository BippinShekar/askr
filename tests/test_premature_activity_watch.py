"""
Tests for the same-session rate-limit-resume feature's safety net (Stage 5,
2026-08-11): lifecycle._watch_for_premature_activity /
lifecycle._alert_premature_activity.

Can't verify the outcome by reading the terminal directly (no stable API
for that), so this uses an independent, out-of-band signal instead:
transcript activity before the real reset time is proof real API calls
succeeded, which "wait for reset" should make impossible. If the wrong
rate-limit option got selected (extra usage / upgrade instead of wait),
the session unblocks immediately and the transcript starts growing again —
that's the tell this watches for.
"""

import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.session import lifecycle


class WatchForPrematureActivityTests(unittest.TestCase):
    def _iso(self, seconds_from_now):
        return (datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)).isoformat()

    def test_reset_arrives_with_no_activity_returns_false(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            baseline = os.path.getmtime(f.name)
            with patch.object(lifecycle, "_alert_premature_activity") as mock_alert:
                result = lifecycle._watch_for_premature_activity(
                    f.name, self._iso(0.2), baseline,
                )
        self.assertFalse(result)
        mock_alert.assert_not_called()

    def test_activity_before_reset_returns_true_and_alerts(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            baseline = os.path.getmtime(path)
            time.sleep(0.05)
            # Bump mtime past baseline — simulates the transcript writing
            # new content, i.e. the session resumed early.
            os.utime(path, None)
            with patch.object(lifecycle, "_alert_premature_activity") as mock_alert:
                result = lifecycle._watch_for_premature_activity(
                    path, self._iso(5), baseline, project_path="/proj", session_id="sess-1",
                )
            self.assertTrue(result)
            mock_alert.assert_called_once_with("/proj", "sess-1")
        finally:
            os.remove(path)

    def test_unparseable_reset_time_skips_watch_returns_false(self):
        with patch.object(lifecycle, "_alert_premature_activity") as mock_alert:
            result = lifecycle._watch_for_premature_activity(
                "/some/transcript.jsonl", "not-a-real-timestamp", time.time(),
            )
        self.assertFalse(result)
        mock_alert.assert_not_called()

    def test_missing_transcript_file_does_not_raise(self):
        with patch.object(lifecycle, "_alert_premature_activity") as mock_alert:
            try:
                result = lifecycle._watch_for_premature_activity(
                    "/definitely/does/not/exist.jsonl", self._iso(0.2), time.time(),
                )
            except Exception as e:
                self.fail(f"_watch_for_premature_activity raised: {e}")
        self.assertFalse(result)
        mock_alert.assert_not_called()

    def test_reset_already_passed_returns_false_immediately(self):
        with tempfile.NamedTemporaryFile(suffix=".jsonl") as f:
            baseline = os.path.getmtime(f.name)
            with patch.object(lifecycle, "_alert_premature_activity") as mock_alert:
                result = lifecycle._watch_for_premature_activity(
                    f.name, self._iso(-5), baseline,
                )
        self.assertFalse(result)
        mock_alert.assert_not_called()


class AlertPrematureActivityTests(unittest.TestCase):
    def test_writes_visible_notification_speaks_and_sends_discord(self):
        with tempfile.TemporaryDirectory() as tmp:
            notif_path = os.path.join(tmp, "notification.json")
            with patch.object(lifecycle, "_NOTIFICATION_PATH", notif_path), \
                 patch.object(lifecycle, "_speak") as mock_speak, \
                 patch("askr.clients.discord.send_message") as mock_discord:
                lifecycle._alert_premature_activity("/proj", "sess-1")

            with open(notif_path) as f:
                notif = json.load(f)
            self.assertEqual(notif["type"], "billing_anomaly_alert")
            self.assertIn("Check your Anthropic billing", notif["message"])
            self.assertEqual(notif["project_path"], "/proj")
            self.assertEqual(notif["session_id"], "sess-1")

            mock_speak.assert_called_once()
            self.assertIn("billing", mock_speak.call_args[0][0].lower())

            mock_discord.assert_called_once()
            self.assertIn("URGENT", mock_discord.call_args[0][0])

    def test_never_raises_even_if_every_channel_fails(self):
        with patch.object(lifecycle, "_NOTIFICATION_PATH", "/nonexistent/dir/n.json"), \
             patch.object(lifecycle, "_speak", side_effect=Exception("boom")), \
             patch("askr.clients.discord.send_message", side_effect=Exception("boom")):
            try:
                lifecycle._alert_premature_activity("/proj", "sess-1")
            except Exception as e:
                self.fail(f"_alert_premature_activity raised: {e}")


if __name__ == "__main__":
    unittest.main()
