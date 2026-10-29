"""
Claude Code auto-compacts idle conversations in the background. pre_compact
must not SIGKILL those — there's no live turn to protect (2026-10-29).
"""

import io
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from askr.hooks import pre_compact
from askr.hooks.pre_compact import _idle_seconds_at_compaction


def _ts(minutes_ago):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z")


def _transcript(entries):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    for e in entries:
        f.write(json.dumps(e) + "\n")
    f.close()
    return f.name


def _finished_turn(minutes_ago):
    return [
        {"type": "user", "message": {"content": "do the thing"}, "timestamp": _ts(minutes_ago + 2)},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "done"}]}, "timestamp": _ts(minutes_ago)},
        {"type": "system", "subtype": "stop_hook_summary", "timestamp": _ts(minutes_ago)},
        {"type": "system", "subtype": "turn_duration", "timestamp": _ts(minutes_ago)},
    ]


def test_idle_after_finished_turn_with_recap():
    path = _transcript(_finished_turn(54) + [
        {"type": "system", "subtype": "away_summary", "content": "recap", "timestamp": _ts(22)},
        {"type": "file-history-snapshot"},
        {"type": "last-prompt"},
    ])
    try:
        assert _idle_seconds_at_compaction(path) >= 54 * 60 - 5
    finally:
        os.unlink(path)


def test_mid_turn_is_not_idle():
    path = _transcript(_finished_turn(54) + [
        {"type": "user", "message": {"content": "next task"}, "timestamp": _ts(3)},
        {"type": "assistant", "message": {"content": [{"type": "tool_use"}]}, "timestamp": _ts(1)},
        {"type": "user", "message": {"content": [{"type": "tool_result"}]}, "timestamp": _ts(0)},
        {"type": "api-request", "timestamp": _ts(0)},
    ])
    try:
        assert _idle_seconds_at_compaction(path) is None
    finally:
        os.unlink(path)


def test_new_prompt_after_idle_is_not_idle():
    path = _transcript(_finished_turn(54) + [
        {"type": "user", "message": {"content": "back again"}, "timestamp": _ts(0)},
    ])
    try:
        assert _idle_seconds_at_compaction(path) is None
    finally:
        os.unlink(path)


def test_unreadable_or_missing_transcript_is_unknown():
    assert _idle_seconds_at_compaction("") is None
    assert _idle_seconds_at_compaction("/nonexistent/x.jsonl") is None


def test_partial_first_line_in_tail_window_is_ignored():
    path = _transcript(_finished_turn(10))
    with open(path, "r+b") as f:
        content = f.read()
        f.seek(0)
        f.write(b'{"type": "user", "trunc' + content)
    try:
        with patch.object(pre_compact, "_TRANSCRIPT_TAIL_BYTES", len(content) + 5):
            assert _idle_seconds_at_compaction(path) >= 10 * 60 - 5
    finally:
        os.unlink(path)


def test_main_skips_kill_on_idle_compaction(tmp_path):
    path = _transcript(_finished_turn(30))
    state = tmp_path / "askr_state"
    state.mkdir()
    payload = json.dumps({"transcript_path": path, "trigger": "auto"})
    try:
        with patch.object(pre_compact, "get_state_dir", return_value=str(state)), \
             patch.object(pre_compact, "load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=str(tmp_path)), \
             patch.object(pre_compact, "_find_own_claude_pid", return_value=4242) as find_pid, \
             patch.object(pre_compact.os, "kill") as kill, \
             patch.object(sys, "stdin", io.StringIO(payload)):
            pre_compact.main()
        find_pid.assert_not_called()
        kill.assert_not_called()
        with open(pre_compact._DAEMON_LOG_PATH) as f:
            assert "skipped kill: idle background compaction" in f.read()
    finally:
        os.unlink(path)


def test_main_still_kills_mid_turn(tmp_path):
    path = _transcript(_finished_turn(30) + [
        {"type": "user", "message": {"content": "next"}, "timestamp": _ts(1)},
        {"type": "api-request", "timestamp": _ts(0)},
    ])
    state = tmp_path / "askr_state"
    state.mkdir()
    payload = json.dumps({"transcript_path": path, "trigger": "auto"})
    try:
        with patch.object(pre_compact, "get_state_dir", return_value=str(state)), \
             patch.object(pre_compact, "load_developer", return_value="dev"), \
             patch("askr.session.monitor.find_project_root", return_value=str(tmp_path)), \
             patch.object(pre_compact, "_find_own_claude_pid", return_value=4242), \
             patch("askr.session.lifecycle._find_all_claude_pids_by_project", return_value=[]), \
             patch.object(pre_compact, "_get_tty_for_pid", return_value=None), \
             patch.object(pre_compact, "_spawn_background_finish"), \
             patch.object(pre_compact.os, "kill") as kill, \
             patch.object(sys, "stdin", io.StringIO(payload)):
            pre_compact.main()
        kill.assert_called_once()
        assert kill.call_args[0][0] == 4242
    finally:
        os.unlink(path)
