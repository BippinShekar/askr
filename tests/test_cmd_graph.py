"""
Tests for `askr graph` (2026-08-15) — the CLI rendering layer on top of
askr.state.events_reader's tree reconstruction.
"""

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.cli import askr


def _trigger(session_id, parent_session_id=None, project_path="/proj", trigger_type="context", **kw):
    return {
        "event_type": "trigger_fired", "session_id": session_id,
        "parent_session_id": parent_session_id, "project_path": project_path,
        "trigger_type": trigger_type, "ts": "2026-08-15T14:33:00+00:00", **kw,
    }


class FormatTriggerSummaryTests(unittest.TestCase):
    def test_empty_events_says_no_trigger(self):
        self.assertIn("no trigger recorded", askr._format_trigger_summary([]))

    def test_context_shows_percentage_from_fraction(self):
        summary = askr._format_trigger_summary([_trigger("a", trigger_type="context", context_pct=0.71)])
        self.assertIn("71%", summary)

    def test_quota_shows_percentage_from_whole_number(self):
        summary = askr._format_trigger_summary([_trigger("a", trigger_type="quota", quota_pct=93.0)])
        self.assertIn("93%", summary)

    def test_idle_shows_no_percentage(self):
        summary = askr._format_trigger_summary([_trigger("a", trigger_type="idle")])
        self.assertIn("idle", summary)
        self.assertNotIn("%", summary)

    def test_emergency_shows_no_percentage(self):
        summary = askr._format_trigger_summary([_trigger("a", trigger_type="emergency")])
        self.assertIn("emergency", summary)
        self.assertNotIn("%", summary)

    def test_caps_at_three_most_recent(self):
        events = [_trigger("a", trigger_type=t) for t in ["context", "idle", "quota", "context", "idle"]]
        summary = askr._format_trigger_summary(events)
        # Only the last 3 trigger_type tokens should appear — "quota", "context", "idle"
        self.assertEqual(summary.count("@14:33"), 3)


class BuildGraphTreeTests(unittest.TestCase):
    def test_renders_root_and_child(self):
        from askr.state.events_reader import build_session_tree
        tree = build_session_tree([
            _trigger("aaaaaaaa-1111"),
            _trigger("bbbbbbbb-2222", parent_session_id="aaaaaaaa-1111"),
        ])
        rendered = askr._build_graph_tree(tree)
        buf = io.StringIO()
        from rich.console import Console
        Console(file=buf, width=120).print(rendered)
        output = buf.getvalue()
        self.assertIn("aaaaaaaa", output)
        self.assertIn("bbbbbbbb", output)

    def test_project_path_shown_as_basename(self):
        from askr.state.events_reader import build_session_tree
        tree = build_session_tree([_trigger("a", project_path="/Users/bippin/Desktop/leaps")])
        rendered = askr._build_graph_tree(tree)
        buf = io.StringIO()
        from rich.console import Console
        Console(file=buf, width=120).print(rendered)
        self.assertIn("leaps", buf.getvalue())

    def test_spawn_note_shown_when_present(self):
        from askr.state.events_reader import build_session_tree
        tree = build_session_tree([
            _trigger("a"),
            {"event_type": "companion_spawned", "session_id": None, "parent_session_id": "a",
             "project_path": "/proj", "trigger_type": "quota"},
        ])
        rendered = askr._build_graph_tree(tree)
        buf = io.StringIO()
        from rich.console import Console
        Console(file=buf, width=120).print(rendered)
        self.assertIn("spawned 1", buf.getvalue())


class CmdGraphTests(unittest.TestCase):
    def test_no_events_prints_helpful_message_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "askr_state")
            os.makedirs(state_dir)
            with patch.object(askr, "get_state_dir", return_value=state_dir):
                buf = io.StringIO()
                with redirect_stdout(buf):
                    askr.cmd_graph()
        self.assertIn("No session events recorded yet", buf.getvalue())

    def test_real_events_render_without_raising(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            state_dir = os.path.join(tmp, "askr_state")
            os.makedirs(state_dir)
            with open(os.path.join(state_dir, "events.jsonl"), "w") as f:
                f.write(json.dumps(_trigger("a")) + "\n")
                f.write(json.dumps(_trigger("b", parent_session_id="a", trigger_type="quota", quota_pct=91.0)) + "\n")
            with patch.object(askr, "get_state_dir", return_value=state_dir):
                buf = io.StringIO()
                try:
                    with redirect_stdout(buf):
                        askr.cmd_graph()
                except Exception as e:
                    self.fail(f"cmd_graph raised: {e}")
        output = buf.getvalue()
        self.assertIn("2 session(s)", output)


if __name__ == "__main__":
    unittest.main()
