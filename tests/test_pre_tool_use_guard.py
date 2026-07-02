"""
Tests for askr/hooks/pre_tool_use.py — the PreToolUse implementation guard.
This is the primary architecture/security boundary enforcement in the
codebase (blocks new files, batch edits, shared-interface edits, and
cross-repo writes) and previously had zero test coverage.

Covers:
  - extract_bash_paths / find_cross_repo_bash_path (pure helpers)
  - _handle_bash (Bash cross-repo boundary check)
  - main() end-to-end via stdin injection, for both Bash and Write/Edit
  - the pre-existing Write/Edit/MultiEdit guard pipeline: new-file trigger,
    batch-write trigger, shared-interface trigger, cooldown, previously-
    blocked retry bypass, escape hatch, cross-repo boundary, and the
    askr_state/.claude skip.

All state files (~/.config/askr/guard_session.json, guard_blocks.json) are
redirected to a tmp dir per-test via monkeypatching the module's path
constants directly (same pattern as tests/test_task_approval_gate.py's
session_start._NOTIFICATION_PATH monkeypatch). get_state_dir()'s cwd-relative
lookup is exercised by chdir'ing into a tmp project dir with its own
askr_state/, matching tests/test_multi_developer_e2e.py. Discord sends are
patched everywhere to avoid any real network call.
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from askr.hooks import pre_tool_use


# ---------------------------------------------------------------------------
# extract_bash_paths — pure function, no I/O
# ---------------------------------------------------------------------------

class ExtractBashPathsTests(unittest.TestCase):
    def test_absolute_path_extracted(self):
        self.assertEqual(pre_tool_use.extract_bash_paths("cat /etc/passwd"), ["/etc/passwd"])

    def test_home_relative_path_extracted(self):
        self.assertEqual(
            pre_tool_use.extract_bash_paths("rm ~/Desktop/notes.txt"),
            ["~/Desktop/notes.txt"],
        )

    def test_parent_dir_escape_extracted(self):
        self.assertEqual(
            pre_tool_use.extract_bash_paths("cat ../../etc/passwd"),
            ["../../etc/passwd"],
        )

    def test_multiple_absolute_paths_all_extracted(self):
        self.assertEqual(
            pre_tool_use.extract_bash_paths("cp /tmp/a /tmp/b"),
            ["/tmp/a", "/tmp/b"],
        )

    def test_flags_skipped(self):
        self.assertEqual(
            pre_tool_use.extract_bash_paths("rm -rf /tmp/foo --output=/tmp/bar"),
            ["/tmp/foo"],
        )

    def test_urls_skipped(self):
        self.assertEqual(pre_tool_use.extract_bash_paths("curl https://example.com/path"), [])

    def test_env_var_assignment_skipped(self):
        self.assertEqual(pre_tool_use.extract_bash_paths("FOO=/bar some_cmd"), [])

    def test_bare_relative_tokens_skipped(self):
        self.assertEqual(pre_tool_use.extract_bash_paths("git status src/main.py"), [])

    def test_empty_command_returns_empty_list(self):
        self.assertEqual(pre_tool_use.extract_bash_paths(""), [])

    def test_none_command_returns_empty_list(self):
        self.assertEqual(pre_tool_use.extract_bash_paths(None), [])

    def test_unbalanced_quotes_falls_back_without_raising(self):
        # shlex.split raises ValueError on unbalanced quotes -- must fall back
        # to naive split rather than propagate.
        try:
            result = pre_tool_use.extract_bash_paths('echo "/tmp/foo')
        except Exception as e:
            self.fail(f"extract_bash_paths raised on unbalanced quotes: {e}")
        self.assertIsInstance(result, list)


# ---------------------------------------------------------------------------
# find_cross_repo_bash_path — pure function, takes project_root as an arg
# ---------------------------------------------------------------------------

class FindCrossRepoBashPathTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        os.makedirs(os.path.join(self.root, "src"), exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_path_outside_root_is_returned(self):
        result = pre_tool_use.find_cross_repo_bash_path("cat /etc/passwd", self.root)
        self.assertEqual(result, "/etc/passwd")

    def test_in_repo_path_returns_none(self):
        in_repo = os.path.join(self.root, "src", "main.py")
        result = pre_tool_use.find_cross_repo_bash_path(f"cat {in_repo}", self.root)
        self.assertIsNone(result)

    def test_only_in_repo_paths_among_multiple_returns_none(self):
        a = os.path.join(self.root, "a.py")
        b = os.path.join(self.root, "src", "b.py")
        result = pre_tool_use.find_cross_repo_bash_path(f"diff {a} {b}", self.root)
        self.assertIsNone(result)

    def test_askr_state_path_skipped_even_if_outside_root(self):
        command = "cat /some/other/place/askr_state/notes.md"
        result = pre_tool_use.find_cross_repo_bash_path(command, self.root)
        self.assertIsNone(result)

    def test_dot_claude_path_skipped_even_if_outside_root(self):
        command = "cat /some/other/place/.claude/settings.json"
        result = pre_tool_use.find_cross_repo_bash_path(command, self.root)
        self.assertIsNone(result)

    def test_malformed_command_fails_open(self):
        try:
            result = pre_tool_use.find_cross_repo_bash_path('echo "/etc/passwd', self.root)
        except Exception as e:
            self.fail(f"find_cross_repo_bash_path raised: {e}")
        self.assertIsNone(result)

    def test_invalid_project_root_fails_open(self):
        try:
            result = pre_tool_use.find_cross_repo_bash_path("cat /etc/passwd", None)
        except Exception as e:
            self.fail(f"find_cross_repo_bash_path raised on bad project_root: {e}")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# _handle_bash — integration of the Bash cross-repo check
# ---------------------------------------------------------------------------

class HandleBashTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        os.makedirs(os.path.join(self.project_dir, "askr_state"), exist_ok=True)
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def test_outside_root_path_triggers_block(self):
        with patch("askr.hooks.pre_tool_use._block_tool") as mock_block:
            pre_tool_use._handle_bash({"command": "cat /etc/passwd"})
        mock_block.assert_called_once()
        (reason,), _ = mock_block.call_args
        self.assertIn("/etc/passwd", reason)
        self.assertIn(self.project_dir, reason)

    def test_in_repo_path_does_not_block(self):
        in_repo = os.path.join(self.project_dir, "main.py")
        with patch("askr.hooks.pre_tool_use._block_tool") as mock_block:
            pre_tool_use._handle_bash({"command": f"cat {in_repo}"})
        mock_block.assert_not_called()

    def test_real_block_tool_calls_sys_exit_2(self):
        # Exercise the real _block_tool (not mocked) to confirm the Bash path
        # genuinely calls sys.exit(2) rather than merely constructing a message.
        with self.assertRaises(SystemExit) as cm:
            pre_tool_use._handle_bash({"command": "cat /etc/passwd"})
        self.assertEqual(cm.exception.code, 2)

    def test_missing_askr_state_dir_is_noop(self):
        with patch("askr.state.config.get_state_dir", return_value="/nonexistent/askr_state"):
            with patch("askr.hooks.pre_tool_use._block_tool") as mock_block:
                pre_tool_use._handle_bash({"command": "cat /etc/passwd"})
            mock_block.assert_not_called()

    def test_cwd_inside_nested_worktree_does_not_lock_out_real_root(self):
        # Regression: cwd drifting into a git worktree under .claude/worktrees/
        # (a full checkout, so it has its own duplicate askr_state/) used to
        # make get_state_dir() pick the worktree as project_root, after which
        # even `cd ..` or `pwd`-style absolute-path commands back to the real
        # root were blocked as "cross-repo" — a total self-lockout.
        worktree = os.path.join(self.project_dir, ".claude", "worktrees", "agent-x")
        os.makedirs(os.path.join(worktree, "askr_state"), exist_ok=True)
        os.chdir(worktree)
        with patch("askr.hooks.pre_tool_use._block_tool") as mock_block:
            pre_tool_use._handle_bash({"command": f"ls {self.project_dir}"})
        mock_block.assert_not_called()


# ---------------------------------------------------------------------------
# _block_tool — unit
# ---------------------------------------------------------------------------

class BlockToolTests(unittest.TestCase):
    def test_prints_decision_json_and_exits_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                pre_tool_use._block_tool("some reason")
        self.assertEqual(cm.exception.code, 2)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload, {"decision": "block", "reason": "some reason"})


# ---------------------------------------------------------------------------
# _is_new_file
# ---------------------------------------------------------------------------

class IsNewFileTests(unittest.TestCase):
    def test_nonexistent_path_is_new(self):
        self.assertTrue(pre_tool_use._is_new_file("/definitely/not/here/xyz.py"))

    def test_existing_path_is_not_new(self):
        with tempfile.NamedTemporaryFile() as f:
            self.assertFalse(pre_tool_use._is_new_file(f.name))

    def test_empty_path_is_not_new(self):
        self.assertFalse(pre_tool_use._is_new_file(""))


# ---------------------------------------------------------------------------
# _is_shared_interface — mocked architecture.md content
# ---------------------------------------------------------------------------

class IsSharedInterfaceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self.state_dir = os.path.join(self.project_dir, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _write_arch(self, content):
        with open(os.path.join(self.state_dir, "architecture.md"), "w") as f:
            f.write(content)

    def test_no_architecture_md_returns_false(self):
        self.assertFalse(pre_tool_use._is_shared_interface("widget.py"))

    def test_file_flagged_as_core_interface(self):
        self._write_arch("## Core modules\n`widget.py` is the shared entrypoint for rendering.\n")
        self.assertTrue(pre_tool_use._is_shared_interface("/some/path/widget.py"))

    def test_file_mentioned_with_no_keyword_anywhere_returns_false(self):
        self._write_arch("The file `widget.py` handles rendering, nothing special here.\n")
        self.assertFalse(pre_tool_use._is_shared_interface("/some/path/widget.py"))

    def test_file_not_mentioned_returns_false(self):
        self._write_arch("## Core modules\n`other.py` is shared.\n")
        self.assertFalse(pre_tool_use._is_shared_interface("/some/path/widget.py"))

    def test_empty_path_returns_false(self):
        self.assertFalse(pre_tool_use._is_shared_interface(""))


# ---------------------------------------------------------------------------
# _in_cooldown
# ---------------------------------------------------------------------------

class CooldownTests(unittest.TestCase):
    def test_no_last_trigger_not_in_cooldown(self):
        self.assertFalse(pre_tool_use._in_cooldown({}))

    def test_recent_trigger_is_in_cooldown(self):
        now = datetime.now(timezone.utc).isoformat()
        self.assertTrue(pre_tool_use._in_cooldown({"last_trigger_at": now}))

    def test_old_trigger_not_in_cooldown(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=pre_tool_use._GUARD_COOLDOWN_SECS + 10)).isoformat()
        self.assertFalse(pre_tool_use._in_cooldown({"last_trigger_at": old}))

    def test_malformed_timestamp_not_in_cooldown(self):
        self.assertFalse(pre_tool_use._in_cooldown({"last_trigger_at": "not-a-date"}))


# ---------------------------------------------------------------------------
# _load_blocks / _block_is_expired — _BLOCK_TTL_SECS expiry
# ---------------------------------------------------------------------------

class BlockExpiryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_blocks_path = pre_tool_use._GUARD_BLOCKS_PATH
        pre_tool_use._GUARD_BLOCKS_PATH = os.path.join(self._tmp.name, "guard_blocks.json")

    def tearDown(self):
        pre_tool_use._GUARD_BLOCKS_PATH = self._orig_blocks_path
        self._tmp.cleanup()

    def _write_blocks(self, blocks):
        with open(pre_tool_use._GUARD_BLOCKS_PATH, "w") as f:
            json.dump(blocks, f)

    def test_block_is_expired_true_past_ttl(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=pre_tool_use._BLOCK_TTL_SECS + 10)).isoformat()
        self.assertTrue(pre_tool_use._block_is_expired({"last_blocked": old}, datetime.now(timezone.utc)))

    def test_block_is_expired_false_within_ttl(self):
        recent = datetime.now(timezone.utc).isoformat()
        self.assertFalse(pre_tool_use._block_is_expired({"last_blocked": recent}, datetime.now(timezone.utc)))

    def test_block_is_expired_false_when_missing_timestamp(self):
        self.assertFalse(pre_tool_use._block_is_expired({}, datetime.now(timezone.utc)))

    def test_load_blocks_prunes_expired_entries_and_persists(self):
        old = (datetime.now(timezone.utc) - timedelta(seconds=pre_tool_use._BLOCK_TTL_SECS + 10)).isoformat()
        recent = datetime.now(timezone.utc).isoformat()
        self._write_blocks({
            "/repo/stale.py": {"count": 1, "last_blocked": old},
            "/repo/fresh.py": {"count": 1, "last_blocked": recent},
        })

        blocks = pre_tool_use._load_blocks()
        self.assertNotIn("/repo/stale.py", blocks)
        self.assertIn("/repo/fresh.py", blocks)

        with open(pre_tool_use._GUARD_BLOCKS_PATH) as f:
            on_disk = json.load(f)
        self.assertNotIn("/repo/stale.py", on_disk)

    def test_load_blocks_missing_file_returns_empty(self):
        self.assertEqual(pre_tool_use._load_blocks(), {})

    def test_load_blocks_malformed_json_returns_empty(self):
        with open(pre_tool_use._GUARD_BLOCKS_PATH, "w") as f:
            f.write("not json")
        self.assertEqual(pre_tool_use._load_blocks(), {})


# ---------------------------------------------------------------------------
# main() end-to-end via stdin injection — Bash
# ---------------------------------------------------------------------------

class MainBashEndToEndTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        os.makedirs(os.path.join(self.project_dir, "askr_state"), exist_ok=True)
        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)
        self._orig_stdin = sys.stdin

    def tearDown(self):
        sys.stdin = self._orig_stdin
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _feed(self, payload):
        sys.stdin = io.StringIO(json.dumps(payload))

    def test_bash_with_outside_root_path_blocks_and_exits_2(self):
        self._feed({"tool_name": "Bash", "tool_input": {"command": "cat /etc/passwd"}})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with self.assertRaises(SystemExit) as cm:
                pre_tool_use.main()
        self.assertEqual(cm.exception.code, 2)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["decision"], "block")
        self.assertIn("/etc/passwd", out["reason"])

    def test_bash_with_in_repo_path_passes_and_exits_0(self):
        in_repo = os.path.join(self.project_dir, "main.py")
        self._feed({"tool_name": "Bash", "tool_input": {"command": f"cat {in_repo}"}})
        with self.assertRaises(SystemExit) as cm:
            pre_tool_use.main()
        self.assertEqual(cm.exception.code, 0)


class MainMalformedInputTests(unittest.TestCase):
    def test_malformed_stdin_json_exits_0(self):
        orig_stdin = sys.stdin
        sys.stdin = io.StringIO("not json")
        try:
            with self.assertRaises(SystemExit) as cm:
                pre_tool_use.main()
            self.assertEqual(cm.exception.code, 0)
        finally:
            sys.stdin = orig_stdin

    def test_unrelated_tool_name_exits_0(self):
        orig_stdin = sys.stdin
        sys.stdin = io.StringIO(json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/etc/passwd"}}))
        try:
            with self.assertRaises(SystemExit) as cm:
                pre_tool_use.main()
            self.assertEqual(cm.exception.code, 0)
        finally:
            sys.stdin = orig_stdin


# ---------------------------------------------------------------------------
# main() end-to-end — Write/Edit/MultiEdit guard pipeline
# ---------------------------------------------------------------------------

class WriteEditGuardPipelineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = self._tmp.name
        self.state_dir = os.path.join(self.project_dir, "askr_state")
        os.makedirs(self.state_dir, exist_ok=True)

        self._orig_cwd = os.getcwd()
        os.chdir(self.project_dir)

        # Redirect the guard's persistent state away from the real
        # ~/.config/askr/guard_session.json and guard_blocks.json.
        self._orig_session_path = pre_tool_use._GUARD_SESSION_PATH
        self._orig_blocks_path = pre_tool_use._GUARD_BLOCKS_PATH
        pre_tool_use._GUARD_SESSION_PATH = os.path.join(self.project_dir, "_guard_session.json")
        pre_tool_use._GUARD_BLOCKS_PATH = os.path.join(self.project_dir, "_guard_blocks.json")

        self._orig_stdin = sys.stdin

        # Never hit the network for Discord alerts.
        self._discord_patch = patch("askr.clients.discord.send_message", return_value=(True, ""))
        self._discord_patch.start()

    def tearDown(self):
        self._discord_patch.stop()
        sys.stdin = self._orig_stdin
        pre_tool_use._GUARD_SESSION_PATH = self._orig_session_path
        pre_tool_use._GUARD_BLOCKS_PATH = self._orig_blocks_path
        os.chdir(self._orig_cwd)
        self._tmp.cleanup()

    def _feed(self, payload):
        sys.stdin = io.StringIO(json.dumps(payload))

    def _run_main(self):
        with self.assertRaises(SystemExit) as cm:
            pre_tool_use.main()
        return cm.exception.code

    def _existing_file(self, name, content="pass\n"):
        path = os.path.join(self.project_dir, name)
        with open(path, "w") as f:
            f.write(content)
        return path

    def _guard_log(self):
        path = os.path.join(self.state_dir, "guard_log.md")
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()

    # -- new_file trigger -----------------------------------------------

    @patch("askr.hooks.pre_tool_use._run_guard")
    def test_write_new_file_triggers_guard_and_blocks_when_dirty(self, mock_guard):
        mock_guard.return_value = {
            "clean": False,
            "issues": ["contradicts architecture.md"],
            "summary": "Bad approach.",
        }
        new_path = os.path.join(self.project_dir, "brand_new.py")
        self._feed({"tool_name": "Write", "tool_input": {"file_path": new_path, "content": "x"}})
        code = self._run_main()

        self.assertEqual(code, 2)
        mock_guard.assert_called_once()
        trigger = mock_guard.call_args[0][0]
        self.assertEqual(trigger["reason"], "new_file")
        self.assertEqual(trigger["file_path"], new_path)

        blocks = json.load(open(pre_tool_use._GUARD_BLOCKS_PATH))
        self.assertIn(new_path, blocks)
        self.assertEqual(blocks[new_path]["count"], 1)

        # Blocked writes must not enter cooldown.
        session = json.load(open(pre_tool_use._GUARD_SESSION_PATH))
        self.assertIsNone(session.get("last_trigger_at"))

        self.assertIn("[BLOCKED]", self._guard_log())
        self.assertIn("contradicts architecture.md", self._guard_log())

    @patch("askr.hooks.pre_tool_use._run_guard")
    def test_write_new_file_clean_result_allows_and_enters_cooldown(self, mock_guard):
        mock_guard.return_value = {"clean": True}
        new_path = os.path.join(self.project_dir, "brand_new2.py")
        self._feed({"tool_name": "Write", "tool_input": {"file_path": new_path}})
        code = self._run_main()

        self.assertEqual(code, 0)
        session = json.load(open(pre_tool_use._GUARD_SESSION_PATH))
        self.assertIsNotNone(session["last_trigger_at"])

    def test_multiedit_new_file_does_not_trigger_new_file_reason(self):
        # new_file trigger is Write-specific; MultiEdit on a not-yet-existing
        # path must not fire it.
        new_path = os.path.join(self.project_dir, "not_yet.py")
        with patch("askr.hooks.pre_tool_use._run_guard") as mock_guard:
            self._feed({"tool_name": "MultiEdit", "tool_input": {"file_path": new_path}})
            code = self._run_main()
        self.assertEqual(code, 0)
        mock_guard.assert_not_called()

    # -- batch_writes trigger --------------------------------------------

    @patch("askr.hooks.pre_tool_use._run_guard")
    def test_third_edit_triggers_batch_writes(self, mock_guard):
        mock_guard.return_value = {"clean": True}
        paths = [self._existing_file(n) for n in ("a.py", "b.py", "c.py")]

        for path in paths:
            self._feed({"tool_name": "Edit", "tool_input": {"file_path": path}})
            self._run_main()

        self.assertEqual(mock_guard.call_count, 1)
        trigger = mock_guard.call_args[0][0]
        self.assertEqual(trigger["reason"], "batch_writes")
        self.assertEqual(trigger["file_path"], paths[2])

    # -- shared_interface trigger ------------------------------------------

    @patch("askr.hooks.pre_tool_use._run_guard")
    def test_shared_interface_edit_triggers_guard(self, mock_guard):
        arch_path = os.path.join(self.state_dir, "architecture.md")
        with open(arch_path, "w") as f:
            f.write("## Core\n`widget.py` is a core shared entrypoint.\n")
        path = self._existing_file("widget.py")

        mock_guard.return_value = {"clean": True}
        self._feed({"tool_name": "Edit", "tool_input": {"file_path": path}})
        self._run_main()

        mock_guard.assert_called_once()
        trigger = mock_guard.call_args[0][0]
        self.assertEqual(trigger["reason"], "shared_interface")

    # -- cooldown -----------------------------------------------------------

    def test_unrelated_file_is_skipped_during_cooldown(self):
        other = self._existing_file("other.py")
        session = {
            "write_count": 1,
            "last_trigger_at": datetime.now(timezone.utc).isoformat(),
            "session_date": pre_tool_use._today(),
        }
        with open(pre_tool_use._GUARD_SESSION_PATH, "w") as f:
            json.dump(session, f)

        with patch("askr.hooks.pre_tool_use._run_guard") as mock_guard:
            self._feed({"tool_name": "Edit", "tool_input": {"file_path": other}})
            code = self._run_main()
        self.assertEqual(code, 0)
        mock_guard.assert_not_called()

    @patch("askr.hooks.pre_tool_use._run_guard")
    def test_previously_blocked_file_bypasses_cooldown_on_retry(self, mock_guard):
        path = self._existing_file("blocked.py")

        session = {
            "write_count": 1,
            "last_trigger_at": datetime.now(timezone.utc).isoformat(),
            "session_date": pre_tool_use._today(),
        }
        with open(pre_tool_use._GUARD_SESSION_PATH, "w") as f:
            json.dump(session, f)

        blocks = {
            path: {
                "count": 1,
                "last_blocked": datetime.now(timezone.utc).isoformat(),
                "trigger_reason": "new_file",
                "issues": ["bad"],
            }
        }
        with open(pre_tool_use._GUARD_BLOCKS_PATH, "w") as f:
            json.dump(blocks, f)

        mock_guard.return_value = {"clean": True}
        self._feed({"tool_name": "Edit", "tool_input": {"file_path": path}})
        self._run_main()

        mock_guard.assert_called_once()
        trigger = mock_guard.call_args[0][0]
        self.assertEqual(trigger["reason"], "new_file")  # reused from the prior block entry

    # -- escape hatch ---------------------------------------------------

    def test_escape_hatch_after_repeated_blocks_allows_through(self):
        path = self._existing_file("stubborn.py")
        blocks = {
            path: {
                "count": pre_tool_use._ESCAPE_HATCH_COUNT,
                "last_blocked": datetime.now(timezone.utc).isoformat(),
                "trigger_reason": "new_file",
                "issues": ["still bad"],
            }
        }
        with open(pre_tool_use._GUARD_BLOCKS_PATH, "w") as f:
            json.dump(blocks, f)

        with patch("askr.hooks.pre_tool_use._run_guard") as mock_guard:
            self._feed({"tool_name": "Edit", "tool_input": {"file_path": path}})
            code = self._run_main()

        self.assertEqual(code, 0)
        mock_guard.assert_not_called()  # escape hatch short-circuits before the guard call

        remaining = json.load(open(pre_tool_use._GUARD_BLOCKS_PATH))
        self.assertNotIn(path, remaining)

        log = self._guard_log()
        self.assertIn("Escape hatch [UNRESOLVED]", log)
        self.assertIn("stubborn.py", log)

    # -- cross-repo boundary for Write/Edit -------------------------------

    def test_write_outside_project_root_blocks(self):
        outside_path = "/etc/passwd"
        buf = io.StringIO()
        self._feed({"tool_name": "Write", "tool_input": {"file_path": outside_path, "content": "x"}})
        with contextlib.redirect_stdout(buf):
            code = self._run_main()
        self.assertEqual(code, 2)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["decision"], "block")
        self.assertIn(outside_path, out["reason"])

    # -- askr_state / .claude skip ----------------------------------------

    def test_write_to_askr_state_path_is_skipped_entirely(self):
        path = os.path.join(self.state_dir, "notes.md")
        with patch("askr.hooks.pre_tool_use._run_guard") as mock_guard:
            self._feed({"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}})
            code = self._run_main()
        self.assertEqual(code, 0)
        mock_guard.assert_not_called()

    def test_write_to_dot_claude_path_is_skipped_entirely(self):
        path = os.path.join(self.project_dir, ".claude", "settings.json")
        with patch("askr.hooks.pre_tool_use._run_guard") as mock_guard:
            self._feed({"tool_name": "Write", "tool_input": {"file_path": path, "content": "x"}})
            code = self._run_main()
        self.assertEqual(code, 0)
        mock_guard.assert_not_called()


if __name__ == "__main__":
    unittest.main()
