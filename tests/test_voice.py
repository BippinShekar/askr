"""
Tests for askr/clients/voice.py's speak() gating and the config/lifecycle
plumbing it depends on:
  - voice_notifications preference round-trips through ~/.config/askr/config.json
  - speak() no-ops (never raises, never shells out) unless enabled + Darwin + `say` present
  - quota_warned_sessions.json round-trips the same way companioned_sessions.json does
    (now keyed by quota_reset_at timestamps, not session ids)
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

    def test_speak_with_voice_passes_dash_v_flag(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.speak("done", voice="Zarvox")
            args, kwargs = mock_run.call_args
            self.assertEqual(args[0], ["/usr/bin/say", "-v", "Zarvox", "done"])

    def test_empty_text_skips_subprocess_entirely(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak("")
            self.assertFalse(ok)
            self.assertIn("empty", reason)
            mock_run.assert_not_called()


class SpeakSignatureTests(unittest.TestCase):
    def test_speaks_prefix_then_body_in_their_own_voices(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak_signature("Done.", "ship OAuth", "Good News", "Zarvox")
            self.assertTrue(ok)
            self.assertEqual(mock_run.call_count, 2)
            first_args = mock_run.call_args_list[0][0][0]
            second_args = mock_run.call_args_list[1][0][0]
            self.assertEqual(first_args, ["/usr/bin/say", "-v", "Good News", "Done."])
            self.assertEqual(second_args, ["/usr/bin/say", "-v", "Zarvox", "ship OAuth"])

    def test_disabled_never_touches_subprocess(self):
        with patch("askr.state.config.load_voice_enabled", return_value=False), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak_signature("Done.", "ship OAuth", "Good News", "Zarvox")
            self.assertFalse(ok)
            mock_run.assert_not_called()

    def test_empty_body_only_speaks_prefix(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.speak_signature("Done.", "", "Good News", "Zarvox")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args, ["/usr/bin/say", "-v", "Good News", "Done."])

    def test_empty_prefix_only_speaks_body(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.speak_signature("", "ship OAuth", "Good News", "Zarvox")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args, ["/usr/bin/say", "-v", "Zarvox", "ship OAuth"])

    def test_both_empty_touches_subprocess_not_at_all(self):
        with patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.speak_signature("", "", "Good News", "Zarvox")
            self.assertTrue(ok)
            mock_run.assert_not_called()


class VoiceLogTests(unittest.TestCase):
    """
    Every spoken-output attempt — successful or gated off — must land in
    voice_log.jsonl with its text, timestamp, whether it actually played,
    why not if it didn't, and whatever caller context was passed in. Added
    2026-07-09 after a repeated-announcement incident that could only be
    diagnosed by reading code and guessing at the mechanism, with no way to
    confirm from disk which call site actually fired or how many times.
    """

    def _read_log(self, path):
        with open(path) as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_successful_speak_is_logged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=True), \
                 patch("platform.system", return_value="Darwin"), \
                 patch("shutil.which", return_value="/usr/bin/say"), \
                 patch("subprocess.run"):
                voice.speak("hello world", context={"source": "test.case", "project_path": "/tmp/proj"})
            entries = self._read_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["text"], "hello world")
            self.assertTrue(entries[0]["spoken"])
            self.assertEqual(entries[0]["source"], "test.case")
            self.assertEqual(entries[0]["project_path"], "/tmp/proj")
            self.assertIn("ts", entries[0])

    def test_gated_off_speak_is_still_logged_with_reason(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=False):
                voice.speak("hello world", context={"source": "test.case"})
            entries = self._read_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertFalse(entries[0]["spoken"])
            self.assertIn("disabled", entries[0]["reason"])

    def test_empty_text_is_not_logged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=True):
                voice.speak("")
            self.assertFalse(os.path.exists(log_path))

    def test_speak_signature_logs_combined_prefix_and_body(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=True), \
                 patch("platform.system", return_value="Darwin"), \
                 patch("shutil.which", return_value="/usr/bin/say"), \
                 patch("subprocess.run"):
                voice.speak_signature("Done.", "ship OAuth", "Good News", "Zarvox")
            entries = self._read_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["text"], "Done. ship OAuth")

    def test_context_none_still_logs_without_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=False):
                voice.speak("hello")
            entries = self._read_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertNotIn("source", entries[0])

    def test_announce_forwards_context_through_to_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "voice_log.jsonl")
            with patch.object(voice, "_VOICE_LOG_PATH", log_path), \
                 patch("askr.state.config.load_voice_enabled", return_value=True), \
                 patch("askr.state.config.load_voice_mode", return_value="single"), \
                 patch("askr.state.config.load_voice_single", return_value="Zarvox"), \
                 patch("platform.system", return_value="Darwin"), \
                 patch("shutil.which", return_value="/usr/bin/say"), \
                 patch("subprocess.run"):
                voice.announce("hi", context={"source": "test.announce", "session_id": "sess-1"})
            entries = self._read_log(log_path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]["source"], "test.announce")
            self.assertEqual(entries[0]["session_id"], "sess-1")


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
                self.assertEqual(lifecycle._load_quota_warned_windows(), set())

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_warned_sessions.json")
            with patch.object(lifecycle, "_QUOTA_WARNED_SESSIONS_PATH", path):
                lifecycle._save_quota_warned_windows({"2026-07-03T10:00:00Z", "2026-07-03T15:00:00Z"})
                self.assertEqual(
                    lifecycle._load_quota_warned_windows(),
                    {"2026-07-03T10:00:00Z", "2026-07-03T15:00:00Z"},
                )

    def test_corrupt_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_warned_sessions.json")
            with open(path, "w") as f:
                f.write("not json")
            with patch.object(lifecycle, "_QUOTA_WARNED_SESSIONS_PATH", path):
                self.assertEqual(lifecycle._load_quota_warned_windows(), set())


class QuotaTriggeredWindowsRoundTripTests(unittest.TestCase):
    def test_missing_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_triggered_windows.json")
            with patch.object(lifecycle, "_QUOTA_TRIGGERED_WINDOWS_PATH", path):
                self.assertEqual(lifecycle._load_quota_triggered_windows(), set())

    def test_save_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_triggered_windows.json")
            with patch.object(lifecycle, "_QUOTA_TRIGGERED_WINDOWS_PATH", path):
                lifecycle._save_quota_triggered_windows({"2026-07-03T10:00:00Z", "2026-07-03T15:00:00Z"})
                self.assertEqual(
                    lifecycle._load_quota_triggered_windows(),
                    {"2026-07-03T10:00:00Z", "2026-07-03T15:00:00Z"},
                )

    def test_corrupt_file_returns_empty_set(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "quota_triggered_windows.json")
            with open(path, "w") as f:
                f.write("not json")
            with patch.object(lifecycle, "_QUOTA_TRIGGERED_WINDOWS_PATH", path):
                self.assertEqual(lifecycle._load_quota_triggered_windows(), set())


class PruneCompanionedSessionsTests(unittest.TestCase):
    """
    Regression coverage for the 2026-07-09 fix: companioned_sessions must only
    lose an entry once the session is genuinely stale (absent from live stats),
    never just because one turn ended — that was the bug behind repeated
    "context high, opening a companion" voice announcements.
    """

    def test_live_session_is_kept(self):
        companioned = {"session-a"}
        all_stats = [{"session_id": "session-a", "context_pct": 0.7}]
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(lifecycle, "_COMPANIONED_SESSIONS_PATH", os.path.join(tmpdir, "c.json")):
                result = lifecycle._prune_companioned_sessions(companioned, all_stats)
        self.assertEqual(result, {"session-a"})

    def test_stale_session_absent_from_stats_is_dropped(self):
        companioned = {"session-a", "session-b"}
        all_stats = [{"session_id": "session-a", "context_pct": 0.7}]  # session-b gone
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(lifecycle, "_COMPANIONED_SESSIONS_PATH", os.path.join(tmpdir, "c.json")):
                result = lifecycle._prune_companioned_sessions(companioned, all_stats)
        self.assertEqual(result, {"session-a"})

    def test_no_stale_entries_skips_disk_write(self):
        companioned = {"session-a"}
        all_stats = [{"session_id": "session-a", "context_pct": 0.7}]
        path = os.path.join(tempfile.mkdtemp(), "c.json")
        with patch.object(lifecycle, "_COMPANIONED_SESSIONS_PATH", path):
            lifecycle._prune_companioned_sessions(companioned, all_stats)
        self.assertFalse(os.path.exists(path))  # nothing changed, nothing written

    def test_stop_hook_no_longer_clears_companioned_session_mid_session(self):
        # The bug: stop.py used to discard session_id from companioned_sessions
        # on every Stop firing (i.e. every turn), not just at true session end.
        # Assert the removed call sites are gone for good (checking the actual
        # call syntax, not just the word — this module's own comments now
        # document the removed bug and mention these names in prose).
        import inspect
        source = inspect.getsource(stop_module.main)
        self.assertNotIn("deregister_session(session_id)", source)
        self.assertNotIn("_load_companioned_sessions()", source)


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

    def test_ignores_tool_result_entries_logged_as_user(self):
        # Real transcripts log tool_result blocks under type "user" — the last
        # "user" line in a turn with tool calls is almost always one of these,
        # timestamped right before Stop fires, not when the human last typed.
        with tempfile.TemporaryDirectory() as tmpdir:
            now = datetime.datetime.now(datetime.timezone.utc)
            real_user_ts = (now - datetime.timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
            tool_result_ts = (now - datetime.timedelta(seconds=3)).isoformat().replace("+00:00", "Z")
            path = os.path.join(tmpdir, "transcript.jsonl")
            with open(path, "w") as f:
                f.write(json.dumps({
                    "type": "user",
                    "timestamp": real_user_ts,
                    "message": {"content": [{"type": "text", "text": "go ahead"}]},
                }) + "\n")
                f.write(json.dumps({
                    "type": "user",
                    "timestamp": tool_result_ts,
                    "message": {"content": [{"type": "tool_result", "content": "ok"}]},
                }) + "\n")
            elapsed = stop_module._turn_elapsed_seconds(path)
            self.assertGreaterEqual(elapsed, 85)


def _write_agent_dispatch(tmpdir, tool_use_id="toolu_agent1", completed=True, extra_id=None):
    """Build a transcript: an assistant turn dispatches an Agent subagent,
    optionally followed by a later turn containing its task-notification."""
    path = os.path.join(tmpdir, "transcript.jsonl")
    with open(path, "w") as f:
        f.write(json.dumps({
            "type": "assistant",
            "message": {"content": [
                {"type": "tool_use", "id": tool_use_id, "name": "Agent", "input": {}},
            ]},
        }) + "\n")
        f.write(json.dumps({
            "type": "user",
            "message": {"content": [
                {"type": "tool_result", "tool_use_id": tool_use_id,
                 "content": "Async agent launched successfully. agentId: abc123"},
            ]},
        }) + "\n")
        if completed:
            f.write(json.dumps({
                "type": "user",
                "message": {"content": (
                    f"<task-notification>\n<task-id>abc123</task-id>\n"
                    f"<tool-use-id>{extra_id or tool_use_id}</tool-use-id>\n"
                    f"<status>completed</status>\n</task-notification>"
                )},
            }) + "\n")
    return path


class HasOutstandingSubagentTests(unittest.TestCase):
    def test_no_transcript_returns_false(self):
        self.assertFalse(stop_module._has_outstanding_subagent(""))
        self.assertFalse(stop_module._has_outstanding_subagent("/no/such/file.jsonl"))

    def test_no_agent_dispatch_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_transcript(tmpdir, ["2026-07-09T00:00:00Z"])
            self.assertFalse(stop_module._has_outstanding_subagent(path))

    def test_dispatched_and_completed_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_agent_dispatch(tmpdir, completed=True)
            self.assertFalse(stop_module._has_outstanding_subagent(path))

    def test_dispatched_but_not_yet_completed_returns_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_agent_dispatch(tmpdir, completed=False)
            self.assertTrue(stop_module._has_outstanding_subagent(path))

    def test_notification_for_a_different_tool_use_id_does_not_clear_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_agent_dispatch(tmpdir, tool_use_id="toolu_agent1",
                                          completed=True, extra_id="toolu_someone_else")
            self.assertTrue(stop_module._has_outstanding_subagent(path))


class SpeakSessionDoneGatingTests(unittest.TestCase):
    def test_stays_silent_while_subagent_outstanding_even_with_completed_goal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_agent_dispatch(tmpdir, completed=False)
            with patch("askr.clients.voice.announce") as mock_announce:
                stop_module._speak_session_done(["ship OAuth"], transcript_path=path)
                mock_announce.assert_not_called()

    def test_speaks_once_subagent_has_reported_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = _write_agent_dispatch(tmpdir, completed=True)
            with patch("askr.clients.voice.announce") as mock_announce:
                stop_module._speak_session_done(["ship OAuth"], transcript_path=path)
                mock_announce.assert_called_once()
                args, kwargs = mock_announce.call_args
                self.assertEqual(args[0], "ship OAuth")
                self.assertEqual(kwargs["prefix"], "Done.")

    def test_completed_goal_always_speaks_even_on_fast_turn(self):
        with patch("askr.clients.voice.announce") as mock_announce:
            stop_module._speak_session_done(["ship OAuth"], transcript_path="")
            mock_announce.assert_called_once()
            args, kwargs = mock_announce.call_args
            self.assertEqual(args[0], "ship OAuth")
            self.assertEqual(kwargs["prefix"], "Done.")

    def test_fast_turn_no_goals_stays_silent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            recent = (datetime.datetime.now(datetime.timezone.utc)
                      - datetime.timedelta(seconds=5)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [recent])
            with patch("askr.clients.voice.announce") as mock_announce:
                stop_module._speak_session_done([], transcript_path=path)
                mock_announce.assert_not_called()

    def test_slow_turn_no_goals_speaks_generic_done(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old = (datetime.datetime.now(datetime.timezone.utc)
                   - datetime.timedelta(seconds=90)).isoformat().replace("+00:00", "Z")
            path = _write_transcript(tmpdir, [old])
            with patch("askr.clients.voice.announce") as mock_announce:
                stop_module._speak_session_done([], transcript_path=path)
                mock_announce.assert_called_once()
                args, kwargs = mock_announce.call_args
                self.assertIn(args[0], stop_module._GENERIC_DONE_PHRASES)
                self.assertEqual(kwargs["prefix"], "Done.")

    def test_respects_configured_voice_style(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "config.json")
            with patch.object(state_config, "CONFIG_PATH", cfg_path):
                state_config.save_voice_enabled(True)
                state_config.save_voice_style("Daniel", "Ralph")
                with patch("askr.state.config.load_voice_enabled", return_value=True), \
                     patch("askr.state.config.load_voice_mode", return_value="dual"), \
                     patch("askr.state.config.load_voice_prefix", return_value="Daniel"), \
                     patch("askr.state.config.load_voice_body", return_value="Ralph"), \
                     patch("platform.system", return_value="Darwin"), \
                     patch("shutil.which", return_value="/usr/bin/say"), \
                     patch("subprocess.run") as mock_run:
                    stop_module._speak_session_done(["ship OAuth"], transcript_path="")
                    first_args = mock_run.call_args_list[0][0][0]
                    second_args = mock_run.call_args_list[1][0][0]
                    self.assertEqual(first_args, ["/usr/bin/say", "-v", "Daniel", "Done."])
                    self.assertEqual(second_args, ["/usr/bin/say", "-v", "Ralph", "ship OAuth"])


class AnnounceTests(unittest.TestCase):
    def test_dual_mode_speaks_prefix_then_message(self):
        with patch("askr.state.config.load_voice_mode", return_value="dual"), \
             patch("askr.state.config.load_voice_prefix", return_value="Good News"), \
             patch("askr.state.config.load_voice_body", return_value="Zarvox"), \
             patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.announce("quota at 90 percent")
            first_args = mock_run.call_args_list[0][0][0]
            second_args = mock_run.call_args_list[1][0][0]
            self.assertEqual(first_args, ["/usr/bin/say", "-v", "Good News", "Askr."])
            self.assertEqual(second_args, ["/usr/bin/say", "-v", "Zarvox", "quota at 90 percent"])

    def test_single_mode_speaks_message_in_one_voice_only(self):
        with patch("askr.state.config.load_voice_mode", return_value="single"), \
             patch("askr.state.config.load_voice_single", return_value="Samantha"), \
             patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.announce("quota at 90 percent")
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertEqual(args, ["/usr/bin/say", "-v", "Samantha", "quota at 90 percent"])

    def test_single_mode_empty_message_skips_subprocess(self):
        with patch("askr.state.config.load_voice_mode", return_value="single"), \
             patch("askr.state.config.load_voice_single", return_value="Zarvox"), \
             patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            ok, reason = voice.announce("")
            self.assertFalse(ok)
            mock_run.assert_not_called()

    def test_dual_mode_empty_prefix_and_message_skips_subprocess(self):
        with patch("askr.state.config.load_voice_mode", return_value="dual"), \
             patch("askr.state.config.load_voice_prefix", return_value="Good News"), \
             patch("askr.state.config.load_voice_body", return_value="Zarvox"), \
             patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.announce("", prefix="")
            mock_run.assert_not_called()

    def test_custom_prefix_used_in_dual_mode(self):
        with patch("askr.state.config.load_voice_mode", return_value="dual"), \
             patch("askr.state.config.load_voice_prefix", return_value="Good News"), \
             patch("askr.state.config.load_voice_body", return_value="Zarvox"), \
             patch("askr.state.config.load_voice_enabled", return_value=True), \
             patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"), \
             patch("subprocess.run") as mock_run:
            voice.announce("ship OAuth", prefix="Done.")
            first_args = mock_run.call_args_list[0][0][0]
            self.assertEqual(first_args, ["/usr/bin/say", "-v", "Good News", "Done."])


class VoiceModeConfigRoundTripTests(unittest.TestCase):
    def test_default_mode_is_dual(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                self.assertEqual(state_config.load_voice_mode(), "dual")

    def test_save_then_load_mode_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                state_config.save_voice_mode("single")
                self.assertEqual(state_config.load_voice_mode(), "single")

    def test_default_single_voice(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                self.assertEqual(state_config.load_voice_single(), state_config.DEFAULT_VOICE_SINGLE)

    def test_save_then_load_single_voice_round_trips(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(state_config, "CONFIG_PATH", os.path.join(tmpdir, "config.json")):
                state_config.save_voice_single("Alex")
                self.assertEqual(state_config.load_voice_single(), "Alex")


if __name__ == "__main__":
    unittest.main()
