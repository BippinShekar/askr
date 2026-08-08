"""
Tests for post_tool_use.py's CLAUDE.md bullet-reminder extension (2026-08-08).

Root cause this addresses: askr's own decisions.jsonl reminder already fights
adherence decay by reprinting the top 5 settled decisions every 10 tool uses
(Phase 3.10 S6) — but CLAUDE.md's own behavioral/style rules (e.g. "terse
comments") never got the same treatment, despite decaying the same way over
a long session. Confirmed on leaps' actual CLAUDE.md (44 lines, rule clearly
present and not truncated) that this isn't a context-eviction problem — the
rule is right there the whole time — it's a pure instruction-salience problem
this periodic reminder is meant to counteract.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import post_tool_use


class LoadClaudeMdBulletsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write_claude_md(self, content):
        with open(os.path.join(self.project_root, "CLAUDE.md"), "w") as f:
            f.write(content)

    def test_extracts_bolded_leadin_of_top_level_bullets(self):
        self._write_claude_md(
            "- **Be direct.** No preamble.\n"
            "- **Flag problems first.** Say so before implementing.\n"
        )
        bullets = post_tool_use._load_claude_md_bullets(self.project_root)
        self.assertEqual(bullets, ["Be direct.", "Flag problems first."])

    def test_extracts_bullets_outside_askr_managed_fences(self):
        # Mirrors leaps' actual CLAUDE.md: a manually-added "Code Comment
        # Style" section sitting after askr's own fenced blocks.
        self._write_claude_md(
            "<!-- askr:behavioral-start -->\n"
            "- **Be direct.** No preamble.\n"
            "<!-- askr:behavioral-end -->\n"
            "\n"
            "## Code Comment Style\n"
            "\n"
            "- **Inline comments: 1-2 lines max, caveman-terse.** State the fact only.\n"
        )
        bullets = post_tool_use._load_claude_md_bullets(self.project_root)
        self.assertIn("Be direct.", bullets)
        self.assertIn("Inline comments: 1-2 lines max, caveman-terse.", bullets)

    def test_ignores_non_bold_bullets_and_continuation_lines(self):
        self._write_claude_md(
            "- plain bullet, no bold\n"
            "- **Real rule.** With a wrapped\n"
            "  continuation line that is not itself a bullet.\n"
        )
        bullets = post_tool_use._load_claude_md_bullets(self.project_root)
        self.assertEqual(bullets, ["Real rule."])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(post_tool_use._load_claude_md_bullets(self.project_root), [])

    def test_caps_at_max_bullets(self):
        lines = "\n".join(f"- **Rule {i}.** detail" for i in range(20))
        self._write_claude_md(lines + "\n")
        bullets = post_tool_use._load_claude_md_bullets(self.project_root)
        self.assertEqual(len(bullets), post_tool_use._MAX_CLAUDE_MD_REMINDER_BULLETS)
        self.assertEqual(bullets[0], "Rule 0.")

    def test_numbered_list_items_not_treated_as_bullets(self):
        # Implementation Guard's numbered list must not be picked up here —
        # it's covered by the guard hook directly, not this text reminder.
        self._write_claude_md("1. Check decisions.jsonl\n2. Check failed_approaches.md\n")
        self.assertEqual(post_tool_use._load_claude_md_bullets(self.project_root), [])


class MaybeRefreshConstraintsIncludesClaudeMdTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = os.path.join(self._tmp.name, "proj")
        self.state_dir = os.path.join(self.project_root, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        with open(os.path.join(self.project_root, "CLAUDE.md"), "w") as f:
            f.write("- **Write terse comments.** One line max.\n")

        self._orig_counter_path = post_tool_use._TURN_COUNTER_PATH
        post_tool_use._TURN_COUNTER_PATH = os.path.join(self._tmp.name, "turn_counter.json")

    def tearDown(self):
        post_tool_use._TURN_COUNTER_PATH = self._orig_counter_path
        self._tmp.cleanup()

    def test_prints_claude_md_rule_on_the_nth_call(self):
        from unittest.mock import patch
        import io
        import contextlib

        with patch("askr.hooks.post_tool_use.get_state_dir", return_value=self.state_dir):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                for _ in range(post_tool_use._REFRESH_EVERY_N):
                    post_tool_use._maybe_refresh_constraints()

        self.assertIn("Write terse comments.", buf.getvalue())

    def test_silent_before_the_nth_call(self):
        from unittest.mock import patch
        import io
        import contextlib

        with patch("askr.hooks.post_tool_use.get_state_dir", return_value=self.state_dir):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                for _ in range(post_tool_use._REFRESH_EVERY_N - 1):
                    post_tool_use._maybe_refresh_constraints()

        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
