"""
Tests for per-project voice config overrides (askr_state/config.json) taking
precedence over the global machine-level default (~/.config/askr/config.json).

Added 2026-09-03: `askr init` used to write voice_notifications/voice_mode/
voice_single/voice_prefix/voice_body only to the global config, so running
init in one repo silently changed voice behavior for every other repo on the
machine. See askr_state/decisions.jsonl, 2026-09-03 (supersedes 2026-07-02's
"voice is global-only" decision).
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.clients import voice
from askr.state import config as state_config


class _IsolatedConfigMixin:
    """Isolates both the global config file and a fake project directory
    (with its own askr_state/config.json) so tests never touch real machine
    state and never depend on the repo's own askr_state/."""

    def setUp(self):
        super().setUp()
        self._global_tmp = tempfile.TemporaryDirectory()
        self._project_tmp = tempfile.TemporaryDirectory()
        self.project_path = self._project_tmp.name
        self._global_patch = patch.object(
            state_config, "CONFIG_PATH", os.path.join(self._global_tmp.name, "config.json")
        )
        self._global_patch.start()

    def tearDown(self):
        self._global_patch.stop()
        self._global_tmp.cleanup()
        self._project_tmp.cleanup()
        super().tearDown()


class VoiceProjectOverrideTests(_IsolatedConfigMixin, unittest.TestCase):
    def test_no_project_override_falls_back_to_global(self):
        state_config.save_voice_enabled(True)
        self.assertTrue(state_config.load_voice_enabled(self.project_path))

    def test_project_override_beats_global_enabled(self):
        state_config.save_voice_enabled(True)
        state_config.save_project_config({"voice_notifications": False}, self.project_path)
        self.assertFalse(state_config.load_voice_enabled(self.project_path))

    def test_project_override_beats_global_disabled(self):
        state_config.save_voice_enabled(False)
        state_config.save_project_config({"voice_notifications": True}, self.project_path)
        self.assertTrue(state_config.load_voice_enabled(self.project_path))

    def test_global_change_does_not_affect_project_override(self):
        state_config.save_project_config({"voice_mode": "single", "voice_single": "Alex"}, self.project_path)
        state_config.save_voice_mode("dual")
        state_config.save_voice_style("Good News", "Zarvox")
        self.assertEqual(state_config.load_voice_mode(self.project_path), "single")
        self.assertEqual(state_config.load_voice_single(self.project_path), "Alex")

    def test_project_override_for_signature_voices(self):
        state_config.save_voice_style("Good News", "Zarvox")
        state_config.save_project_config(
            {"voice_mode": "dual", "voice_prefix": "Daniel", "voice_body": "Ralph"}, self.project_path
        )
        self.assertEqual(state_config.load_voice_prefix(self.project_path), "Daniel")
        self.assertEqual(state_config.load_voice_body(self.project_path), "Ralph")

    def test_unrelated_project_is_unaffected(self):
        """The exact bug reported: askr init in project B must not change
        what project A's daemon calls resolve to."""
        project_a = self.project_path
        project_b_tmp = tempfile.TemporaryDirectory()
        try:
            project_b = project_b_tmp.name
            state_config.save_project_config({"voice_notifications": True}, project_a)
            state_config.save_voice_enabled(True)  # global default, e.g. set during project B's init
            state_config.save_project_config({"voice_notifications": False}, project_b)

            self.assertTrue(state_config.load_voice_enabled(project_a))
            self.assertFalse(state_config.load_voice_enabled(project_b))
        finally:
            project_b_tmp.cleanup()

    def test_cwd_default_still_works_for_hook_subprocesses(self):
        """Hooks run with cwd == project root and never pass project_path
        explicitly — load_voice_enabled(None) must still resolve via cwd."""
        cwd = os.getcwd()
        try:
            os.chdir(self.project_path)
            state_config.save_project_config({"voice_notifications": True}, self.project_path)
            self.assertTrue(state_config.load_voice_enabled())
        finally:
            os.chdir(cwd)


class AnnounceProjectPathTests(_IsolatedConfigMixin, unittest.TestCase):
    """announce() must resolve project scope from context["project_path"]
    (the daemon's only way to identify which project it's speaking for,
    since its own cwd is never a project directory)."""

    def setUp(self):
        super().setUp()
        self._voice_log_tmp = tempfile.TemporaryDirectory()
        self._voice_log_patch = patch.object(
            voice, "_VOICE_LOG_PATH", os.path.join(self._voice_log_tmp.name, "voice_log.jsonl")
        )
        self._voice_log_patch.start()

    def tearDown(self):
        self._voice_log_patch.stop()
        self._voice_log_tmp.cleanup()
        super().tearDown()

    def test_announce_uses_project_path_from_context_for_gating(self):
        """Gating happens inside speak()/speak_signature() via _say_preconditions,
        so this must exercise the real dispatch path (not mock speak itself) and
        assert the `say` subprocess never runs."""
        state_config.save_voice_enabled(True)
        state_config.save_project_config({"voice_notifications": False}, self.project_path)

        with patch("askr.clients.voice.shutil.which", return_value="/usr/bin/say"), \
             patch("askr.clients.voice.subprocess.run") as mock_run, \
             patch("askr.clients.voice.platform.system", return_value="Darwin"):
            ok, reason = voice.announce("hello", context={"project_path": self.project_path})
            mock_run.assert_not_called()
            self.assertFalse(ok)
            self.assertEqual(reason, "voice notifications disabled")

    def test_announce_uses_project_path_from_context_for_voice_selection(self):
        state_config.save_voice_enabled(True)
        state_config.save_voice_mode("dual")
        state_config.save_project_config(
            {"voice_mode": "single", "voice_single": "Alex"}, self.project_path
        )

        with patch.object(voice, "speak") as mock_speak:
            voice.announce("hello", context={"project_path": self.project_path})
            mock_speak.assert_called_once()
            self.assertEqual(mock_speak.call_args.kwargs.get("voice"), "Alex")

    def test_explicit_project_path_overrides_context(self):
        other_tmp = tempfile.TemporaryDirectory()
        try:
            state_config.save_voice_enabled(True)
            state_config.save_project_config({"voice_notifications": False}, self.project_path)
            with patch("askr.clients.voice.shutil.which", return_value="/usr/bin/say"), \
                 patch("askr.clients.voice.subprocess.run") as mock_run, \
                 patch("askr.clients.voice.platform.system", return_value="Darwin"):
                ok, reason = voice.announce(
                    "hello",
                    context={"project_path": other_tmp.name},
                    project_path=self.project_path,
                )
                mock_run.assert_not_called()
                self.assertFalse(ok)
        finally:
            other_tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
