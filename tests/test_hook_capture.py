"""
Tests for the temporary diagnostic hook-payload capture (2026-08-11) — built
to answer one open question: does Claude Code fire ANY hook when the real
5-hour usage limit is hit and the "wait for reset / upgrade / extra usage"
menu appears? Wired into all 7 registered hooks (SessionStart,
UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact, Notification)
so whichever one fires — if any — gets caught regardless of which.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.utils import hook_capture


class CaptureHookPayloadTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_path = hook_capture._CAPTURE_PATH
        hook_capture._CAPTURE_PATH = os.path.join(self._tmp.name, "hook_capture.log")

    def tearDown(self):
        hook_capture._CAPTURE_PATH = self._orig_path
        self._tmp.cleanup()

    def _read_entries(self):
        with open(hook_capture._CAPTURE_PATH) as f:
            return [json.loads(l) for l in f if l.strip()]

    def test_appends_one_entry_per_call(self):
        hook_capture.capture_hook_payload("Notification", {"message": "hi", "level": "info"})
        entries = self._read_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["hook"], "Notification")
        self.assertEqual(entries[0]["payload"]["message"], "hi")
        self.assertIn("ts", entries[0])
        self.assertIn("cwd", entries[0])

    def test_multiple_calls_accumulate_in_order(self):
        hook_capture.capture_hook_payload("SessionStart", {"session_id": "a"})
        hook_capture.capture_hook_payload("Stop", {"session_id": "a"})
        hook_capture.capture_hook_payload("PreCompact", {"session_id": "a"})
        entries = self._read_entries()
        self.assertEqual([e["hook"] for e in entries], ["SessionStart", "Stop", "PreCompact"])

    def test_bounded_at_max_entries(self):
        hook_capture._MAX_ENTRIES = 5
        try:
            for i in range(8):
                hook_capture.capture_hook_payload("PostToolUse", {"i": i})
            entries = self._read_entries()
            self.assertEqual(len(entries), 5)
            self.assertEqual([e["payload"]["i"] for e in entries], [3, 4, 5, 6, 7])
        finally:
            hook_capture._MAX_ENTRIES = 1000

    def test_never_raises_on_unwritable_path(self):
        hook_capture._CAPTURE_PATH = "/nonexistent/deeply/nested/path/that/cannot/be/created/x.log"
        try:
            with patch("os.makedirs", side_effect=OSError("nope")):
                hook_capture.capture_hook_payload("Notification", {"message": "x"})
        except Exception as e:
            self.fail(f"capture_hook_payload raised: {e}")

    def test_corrupt_existing_log_does_not_block_new_capture(self):
        with open(hook_capture._CAPTURE_PATH, "w") as f:
            f.write("not valid json at all\n")
        try:
            hook_capture.capture_hook_payload("Stop", {"ok": True})
        except Exception as e:
            self.fail(f"capture_hook_payload raised on corrupt existing log: {e}")
        # The corrupt line is preserved (this is a raw append log, not a
        # JSON-validating one) but the new entry must still be appended.
        with open(hook_capture._CAPTURE_PATH) as f:
            content = f.read()
        self.assertIn('"Stop"', content)


class WiredIntoHooksTests(unittest.TestCase):
    """Confirm each hook module actually calls capture_hook_payload from
    within main(), not just that the utility itself works in isolation."""

    def _assert_hook_calls_capture(self, module_name, stdin_payload, extra_patches=None):
        import io
        import importlib
        module = importlib.import_module(module_name)
        importlib.reload(module)

        patches = extra_patches or []
        with patch("askr.utils.hook_capture.capture_hook_payload") as mock_capture, \
             patch.object(sys, "stdin", io.StringIO(json.dumps(stdin_payload))):
            from contextlib import ExitStack
            with ExitStack() as stack:
                for p in patches:
                    stack.enter_context(p)
                try:
                    module.main()
                except SystemExit:
                    pass
        mock_capture.assert_called_once()
        return mock_capture.call_args[0]

    def test_notification_hook_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            args = self._assert_hook_calls_capture(
                "askr.hooks.notification", {"message": "", "level": "info"},
                extra_patches=[patch("askr.state.config.get_state_dir", return_value=os.path.join(tmp, "askr_state"))],
            )
        self.assertEqual(args[0], "Notification")

    def test_pre_compact_hook_captures(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "askr_state"))
            args = self._assert_hook_calls_capture(
                "askr.hooks.pre_compact", {"transcript_path": ""},
                extra_patches=[patch("askr.state.config.get_state_dir", return_value=os.path.join(tmp, "askr_state"))],
            )
        self.assertEqual(args[0], "PreCompact")

    def test_pre_tool_use_hook_captures(self):
        orig_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                args = self._assert_hook_calls_capture(
                    "askr.hooks.pre_tool_use", {"tool_name": "Read", "tool_input": {}},
                )
            finally:
                os.chdir(orig_cwd)
        self.assertEqual(args[0], "PreToolUse")


if __name__ == "__main__":
    unittest.main()
