"""
Tests for askr/clients/voice.py's speak() gating and the config/lifecycle
plumbing it depends on:
  - voice_notifications preference round-trips through ~/.config/askr/config.json
  - speak() no-ops (never raises, never shells out) unless enabled + Darwin + `say` present
  - quota_warned_sessions.json round-trips the same way companioned_sessions.json does
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.clients import voice
from askr.state import config as state_config
from askr.session import lifecycle


class VoiceConfigRoundTripTests(unittest.TestCase):
    def test_default_is_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                self.assertFalse(state_config.load_voice_enabled())

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                state_config.save_voice_enabled(True)
                self.assertTrue(state_config.load_voice_enabled())
                state_config.save_voice_enabled(False)
                self.assertFalse(state_config.load_voice_enabled())

    def test_save_voice_enabled_preserves_other_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                state_config.save_developer("bippin")
                state_config.save_voice_enabled(True)
                self.assertEqual(state_config.load_developer(), "bippin")
                self.assertTrue(state_config.load_voice_enabled())


class SpeakGatingTests(unittest.TestCase):
    def test_disabled_never_touches_subprocess(self):
        with patch("askr.state.config.load_voice_enabled", return_value=False), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak("hello")
            self.assertFalse(ok)
            self.assertIn("disabled", reason)
            mock_run.assert_not_called()

    def test_enabled_but_not_darwin_no_ops(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Linux"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak("hello")
            self.assertFalse(ok)
            self.assertIn("macOS-only", reason)
            mock_run.assert_not_called()

    def test_enabled_darwin_but_say_missing_no_ops(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value=None), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak("hello")
            self.assertFalse(ok)
            self.assertIn("say", reason)
            mock_run.assert_not_called()

    def test_enabled_darwin_say_present_invokes_subprocess(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak("done with task")
            self.assertTrue(ok)
            self.assertEqual(reason, "")
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], ["/usr/bin/say", "done with task"])

    def test_subprocess_exception_never_raises(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run", side_effect=OSError("boom")):
            ok, reason = voice.speak("hello")
            self.assertFalse(ok)
            self.assertIn("boom", reason)


class QuotaWarnedSessionsRoundTripTests(unittest.TestCase):
    def test_missing_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_warned_sessions.json")
            with patch.object(lifecycle, "_QUOTA_WARNED_SESSIONS_PATH", path):
                self.assertEqual(lifecycle._load_quota_warned_sessions(), set())

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_warned_sessions.json")
            with patch.object(lifecycle, "_QUOTA_WARNED_SESSIONS_PATH", path):
                lifecycle._save_quota_warned_sessions({"session-a", "session-b"})
                self.assertEqual(
                    lifecycle._load_quota_warned_sessions(), {"session-a", "session-b"}
                )

    def test_corrupt_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_warned_sessions.json")
            with open(path, "w") as f:
                f.write("not json")
            with patch.object(lifecycle, "_QUOTA_WARNED_SESSIONS_PATH", path):
                self.assertEqual(lifecycle._load_quota_warned_sessions(), set())


if __name__ == "__main__":
    unittest.main()
