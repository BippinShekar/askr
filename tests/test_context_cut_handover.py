"""
Tests for context-cut → autonomous talk-only session auto-launch.

Scenario under test: when the daemon triggers at 75% context mid-research
session, the stop hook must auto-launch a continuation session WITHOUT
gating on user approval — even if the last session was talk-only.

Fix is in stop.py:_write_relaunch_notification_if_pending (line 200-206):
    if trigger == "context" and proposed:
        proposed = False
        stop_prompt = "Context was cut mid-session. Continue from where we left off..."
"""

import contextlib
import json
import os
import sys
import tempfile
import datetime
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import askr.hooks.stop as stop_module


def _fresh_checkpoint_pending(trigger="context", context_pct=0.75, age_seconds=5):
    ts = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(seconds=age_seconds)
    ).isoformat()
    return {
        "trigger": trigger,
        "context_pct": context_pct,
        "quota_pct": None,
        "timestamp": ts,
    }


def _direction_talk_only_high_confidence():
    """Talk-only session with clear next action → proposed=True, confidence=0.85."""
    return {
        "direction": "implement the OAuth flow discussed in last session",
        "confidence": 0.85,
        "signal_source": "handover_next_actions",
        "proposed": True,
        "details": {"commit": "abc1234", "session_type": "talk_only", "developer": "bippin"},
    }


def _direction_coding_high_confidence():
    """Coding session → proposed=False (default), confidence=0.85."""
    return {
        "direction": "continue work on askr/hooks/stop.py",
        "confidence": 0.85,
        "signal_source": "handover_next_actions",
        "proposed": False,
        "details": {"commit": "def5678", "session_type": "coding", "developer": "bippin"},
    }


def _direction_low_confidence():
    """No clear signal → confidence 0.50."""
    return {
        "direction": "continue work in askr/ (8 recent changes)",
        "confidence": 0.50,
        "signal_source": "file_path_cluster",
        "details": {"askr/": 8},
    }


class TestContextCutAutoLaunch(unittest.TestCase):
    """
    Core invariant: context-cut trigger must ALWAYS produce notification_type="context"
    (auto-launch), never "direction_proposal" (requires user approval).
    """

    def _run_relaunch(self, tmpdir, pending_data, direction_data, arc=""):
        checkpoint_path = os.path.join(tmpdir, "checkpoint_pending.json")
        notification_path = os.path.join(tmpdir, "notification.json")

        with open(checkpoint_path, "w") as f:
            json.dump(pending_data, f)

        # The function imports lifecycle helpers lazily inside itself, so patch
        # them at their source module. Module-level constants in stop.py can be
        # patched directly on stop_module.
        patches = [
            patch.object(stop_module, "_CHECKPOINT_PENDING", checkpoint_path),
            patch.object(stop_module, "_NOTIFICATION_PATH", notification_path),
            patch("askr.session.lifecycle._infer_direction", return_value=direction_data),
            patch("askr.session.lifecycle._get_next_goal", return_value="ship OAuth"),
            patch("askr.session.lifecycle._write_launch_mode"),
            patch("askr.session.lifecycle._load_allowed_tools", return_value=["Bash", "Read"]),
            patch("askr.session.lifecycle._read_session_arc", return_value=arc),
            patch("askr.state.config.load_developer", return_value="bippin"),
            patch("askr.hooks.stop.os.makedirs"),
            # speak() shells out to real macOS `say` if voice_notifications happens
            # to be enabled in the developer's own global config — never let a test's
            # runtime depend on that ambient machine state.
            patch("askr.clients.voice.speak"),
        ]

        with contextlib.ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)
            result = stop_module._write_relaunch_notification_if_pending({})

        notification = None
        if os.path.exists(notification_path):
            with open(notification_path) as f:
                notification = json.load(f)

        return result, notification

    def test_context_cut_talk_only_auto_launches(self):
        """
        CRITICAL: talk-only session + context trigger → must auto-launch (type="context"),
        not surface for approval (type="direction_proposal").
        This is the exact scenario that was broken before the fix.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context")
            direction = _direction_talk_only_high_confidence()

            ok, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertTrue(ok, "function must return True when notification is written")
            self.assertIsNotNone(notif, "notification.json must be written")
            self.assertEqual(
                notif["type"], "context",
                f"context-cut talk-only must auto-launch (context), got: {notif['type']!r}. "
                f"direction_proposal here means the approval gate bug is back."
            )

    def test_context_cut_prompt_references_continuation(self):
        """Auto-launch prompt for context-cut must say 'Continue from where we left off', not generic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context")
            direction = _direction_talk_only_high_confidence()

            _, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertIn(
                "Continue from where we left off",
                notif.get("prompt", ""),
                "context-cut prompt must orient the new session to continue, not restart"
            )
            self.assertIn(
                direction["direction"],
                notif.get("prompt", ""),
                "context-cut prompt must embed the inferred direction"
            )

    def test_context_cut_coding_session_auto_launches(self):
        """Coding session + context trigger → auto-launch (was always true; regression guard)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context")
            direction = _direction_coding_high_confidence()

            ok, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertEqual(notif["type"], "context")

    def test_natural_stop_talk_only_surfaces_for_approval(self):
        """
        Naturally-ended talk-only session (no context trigger) → direction_proposal.
        Ensures the fix doesn't accidentally auto-launch everything.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # trigger="stop" means session ended normally, not from context limit
            pending = _fresh_checkpoint_pending(trigger="stop")
            direction = _direction_talk_only_high_confidence()

            _, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertEqual(
                notif["type"], "direction_proposal",
                "naturally-ended talk-only session must surface for user approval"
            )

    def test_low_confidence_direction_blocks_regardless_of_trigger(self):
        """Low-confidence direction → direction_confirm (ask user), even for context cuts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context")
            direction = _direction_low_confidence()

            _, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertEqual(
                notif["type"], "direction_confirm",
                "low confidence should always ask user, even mid-context-cut"
            )

    def test_stale_checkpoint_pending_is_ignored(self):
        """checkpoint_pending.json older than 5 min is stale → return False, no notification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context", age_seconds=400)
            direction = _direction_talk_only_high_confidence()

            ok, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertFalse(ok, "stale checkpoint_pending must be silently ignored")
            self.assertIsNone(notif, "no notification should be written for stale checkpoint")

    def test_missing_checkpoint_pending_returns_false(self):
        """If checkpoint_pending.json doesn't exist, function returns False cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            notification_path = os.path.join(tmpdir, "notification.json")
            checkpoint_path = os.path.join(tmpdir, "checkpoint_pending.json")
            # Do NOT create checkpoint_pending.json

            patches = [
                patch.object(stop_module, "_CHECKPOINT_PENDING", checkpoint_path),
                patch.object(stop_module, "_NOTIFICATION_PATH", notification_path),
            ]
            with contextlib.ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                result = stop_module._write_relaunch_notification_if_pending({})

            self.assertFalse(result)

    def test_context_cut_notification_includes_direction_metadata(self):
        """Notification payload must include direction, confidence, and signal for debugging."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = _fresh_checkpoint_pending(trigger="context")
            direction = _direction_talk_only_high_confidence()

            _, notif = self._run_relaunch(tmpdir, pending, direction)

            self.assertIn("direction", notif, "direction field must be in payload")
            self.assertIn("direction_confidence", notif)
            self.assertIn("direction_signal", notif)
            self.assertAlmostEqual(notif["direction_confidence"], 0.85)

    def test_quota_trigger_writes_quota_notification(self):
        """Quota trigger → type='quota', no auto-launch, just inform user."""
        with tempfile.TemporaryDirectory() as tmpdir:
            pending = {
                "trigger": "quota",
                "quota_pct": 92.0,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }

            with tempfile.TemporaryDirectory() as t2:
                checkpoint_path = os.path.join(t2, "checkpoint_pending.json")
                notification_path = os.path.join(t2, "notification.json")
                with open(checkpoint_path, "w") as f:
                    json.dump(pending, f)

                patches = [
                    patch.object(stop_module, "_CHECKPOINT_PENDING", checkpoint_path),
                    patch.object(stop_module, "_NOTIFICATION_PATH", notification_path),
                    patch("askr.session.lifecycle._get_next_goal", return_value=""),
                    patch("askr.session.lifecycle._write_launch_mode"),
                    patch("askr.hooks.stop.os.makedirs"),
                    patch("askr.clients.voice.speak"),
                ]
                with contextlib.ExitStack() as stack:
                    for p in patches:
                        stack.enter_context(p)
                    ok = stop_module._write_relaunch_notification_if_pending({})

                with open(notification_path) as f:
                    notif = json.load(f)

            self.assertTrue(ok)
            self.assertEqual(notif["type"], "quota")
            self.assertIn("Quota", notif["message"])


class TestPreCompactHookRegistration(unittest.TestCase):
    """Verify pre_compact.py is registered in .claude/settings.json."""

    def test_pre_compact_hook_registered(self):
        settings_path = os.path.join(
            os.path.dirname(__file__), "..", ".claude", "settings.json"
        )
        with open(settings_path) as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})
        pre_compact_hooks = hooks.get("PreCompact", [])
        self.assertTrue(
            len(pre_compact_hooks) > 0,
            "PreCompact hook must be registered in .claude/settings.json"
        )

        commands = [
            h.get("command", "") or
            (h.get("hooks") or [{}])[0].get("command", "")
            for h in pre_compact_hooks
        ]
        pre_compact_registered = any("pre_compact.py" in c for c in commands)
        self.assertTrue(
            pre_compact_registered,
            f"pre_compact.py not found in PreCompact hooks. Got: {commands}"
        )

    def test_stop_hook_registered(self):
        settings_path = os.path.join(
            os.path.dirname(__file__), "..", ".claude", "settings.json"
        )
        with open(settings_path) as f:
            settings = json.load(f)

        hooks = settings.get("hooks", {})
        stop_hooks = hooks.get("Stop", [])
        commands = [
            (h.get("hooks") or [{}])[0].get("command", h.get("command", ""))
            for h in stop_hooks
        ]
        stop_registered = any("stop.py" in c for c in commands)
        self.assertTrue(
            stop_registered,
            f"stop.py not found in Stop hooks. Got: {commands}"
        )

    def test_pre_compact_hook_file_exists(self):
        hook_path = os.path.join(
            os.path.dirname(__file__), "..", "askr", "hooks", "pre_compact.py"
        )
        self.assertTrue(
            os.path.exists(hook_path),
            f"pre_compact.py does not exist at expected path: {hook_path}"
        )


class TestInferDirectionSignals(unittest.TestCase):
    """
    Smoke-test _infer_direction against a real git repo (this repo).
    Verifies it returns a valid structure and doesn't crash.
    """

    def test_infer_direction_returns_valid_structure(self):
        from askr.session.lifecycle import _infer_direction
        project_path = os.path.join(os.path.dirname(__file__), "..")
        result = _infer_direction(project_path)

        self.assertIn("direction", result)
        self.assertIn("confidence", result)
        self.assertIn("signal_source", result)
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertIn(
            result["signal_source"],
            {"uncommitted_files", "blockers_md", "handover_next_actions",
             "git_momentum", "commit_scope", "file_path_cluster", "none"},
        )

    def test_infer_direction_proposed_flag_only_on_talk_only(self):
        """proposed key, if present, must be bool — never accidentally truthy on coding sessions."""
        from askr.session.lifecycle import _infer_direction
        project_path = os.path.join(os.path.dirname(__file__), "..")
        result = _infer_direction(project_path)
        if "proposed" in result:
            self.assertIsInstance(result["proposed"], bool)

    def test_infer_direction_never_raises(self):
        """_infer_direction must never raise — it has a safe fallback."""
        from askr.session.lifecycle import _infer_direction
        # Even with a nonsense path, should return the low-confidence fallback
        result = _infer_direction("/nonexistent/path/xyz")
        self.assertIn("direction", result)
        self.assertIn("confidence", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
