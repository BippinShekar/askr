"""
Tests for askr/clients/voice.py's speak() gating and the config/lifecycle
plumbing it depends on:
  - voice_notifications preference round-trips through ~/.config/askr/config.json
  - speak() no-ops (never raises, never shells out) unless enabled + Darwin + `say` present
  - quota_warned_sessions.json round-trips the same way companioned_sessions.json does
"""

import datetime
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
from askr.hooks import stop as stop_module


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

    def test_speak_sends_humanized_text_to_say(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.speak("🔴 **[askr] Claude notification (ERROR)**\nBash(rm -rf /tmp/*) needs approval")
            args, kwargs = mock_run.call_args
            spoken = args[0][1]
            self.assertNotIn("🔴", spoken)
            self.assertNotIn("**", spoken)
            self.assertNotIn("Bash(", spoken)
            self.assertIn("a bash action", spoken)


class HumanizeForSpeechTests(unittest.TestCase):
    def test_empty_string_passthrough(self):
        self.assertEqual(voice.humanize_for_speech(""), "")

    def test_strips_emoji(self):
        self.assertEqual(voice.humanize_for_speech("🔴 error occurred"), "error occurred")

    def test_strips_markdown_symbols(self):
        self.assertEqual(voice.humanize_for_speech("**bold** and `code`"), "bold and code")

    def test_collapses_newlines_into_pauses(self):
        self.assertEqual(voice.humanize_for_speech("line one\nline two"), "line one. line two")

    def test_rewrites_tool_call_syntax(self):
        result = voice.humanize_for_speech("Bash(rm -rf /tmp/foo) needs approval")
        self.assertIn("a bash action", result)
        self.assertNotIn("rm -rf", result)

    def test_caps_length_at_sentence_boundary(self):
        text = "This is a normal sentence. " + ("filler word " * 30)
        result = voice.humanize_for_speech(text, max_len=50)
        self.assertLessEqual(len(result), 50)
        self.assertTrue(result.endswith(".") or result.endswith("…"))

    def test_short_text_unaffected_by_cap(self):
        self.assertEqual(voice.humanize_for_speech("done with task"), "done with task")

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


def _write_transcript(tmpdir, user_timestamps):
    path = os.path.join(tmpdir, "transcript.jsonl")
    with open(path, "w") as f:
        for ts in user_timestamps:
            f.write(json.dumps({"type": "user", "timestamp": ts}) + "\n")
    return path


class TurnElapsedSecondsTests(unittest.TestCase):
    def test_missing_transcript_returns_zero(self):
        self.assertEqual(stop_module._turn_elapsed_seconds(""), 0.0)
        self.assertEqual(stop_module._turn_elapsed_seconds("/no/such/file.jsonl"), 0.0)

    def test_computes_seconds_since_last_user_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_ts = (datetime.datetime.now(datetime.timezone.utc)
                      - datetime.timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [old_ts])
            elapsed = stop_module._turn_elapsed_seconds(path)
            self.assertGreaterEqual(elapsed, 85)
            self.assertLessEqual(elapsed, 100)

    def test_uses_last_user_message_not_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            now = datetime.datetime.now(datetime.timezone.utc)
            far = (now - datetime.timedelta(seconds=500)).isoformat().replace("+00:00", "Z")
            recent = (now - datetime.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [far, recent])
            elapsed = stop_module._turn_elapsed_seconds(path)
            self.assertLess(elapsed, 30)


class SpeakSessionDoneGatingTests(unittest.TestCase):
    def test_completed_goal_always_speaks_even_on_fast_turn(self):
        with patch("askr.clients.voice.speak") as mock_speak:
            stop_module._speak_session_done(["ship OAuth"], transcript_path="")
            mock_speak.assert_called_once_with("Done: ship OAuth")

    def test_fast_turn_no_goals_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recent = (datetime.datetime.now(datetime.timezone.utc)
                      - datetime.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [recent])
            with patch("askr.clients.voice.speak") as mock_speak:
                stop_module._speak_session_done([], transcript_path=path)
                mock_speak.assert_not_called()

    def test_slow_turn_no_goals_speaks_generic_done(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = (datetime.datetime.now(datetime.timezone.utc)
                   - datetime.timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [old])
            with patch("askr.clients.voice.speak") as mock_speak:
                stop_module._speak_session_done([], transcript_path=path)
                mock_speak.assert_called_once_with("Done.")


if __name__ == "__main__":
    unittest.main()
