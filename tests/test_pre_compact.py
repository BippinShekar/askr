"""
PreCompact is observe-only since 2026-10-29: it must never kill, checkpoint,
notify or open a session — only log the compaction and let it run.
"""

import io
import json
import sys
from unittest.mock import patch

from askr.hooks import pre_compact


def _run(tmp_path, payload, state_exists=True):
    state = tmp_path / "askr_state"
    if state_exists:
        state.mkdir()
    with patch.object(pre_compact, "get_state_dir", return_value=str(state)), \
         patch("askr.session.monitor.find_project_root", return_value="/proj"), \
         patch("os.kill") as kill, \
         patch("subprocess.Popen") as popen, \
         patch("subprocess.run") as run, \
         patch("askr.session.checkpoint.create_checkpoint") as checkpoint, \
         patch.object(sys, "stdin", io.StringIO(json.dumps(payload))):
        pre_compact.main()
    for m in (kill, popen, run, checkpoint):
        m.assert_not_called()


def _log(tmp_path):
    try:
        with open(pre_compact._DAEMON_LOG_PATH) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def test_auto_compaction_is_logged_and_allowed(tmp_path):
    _run(tmp_path, {"session_id": "sess-1", "trigger": "auto",
                    "transcript_path": "/x/sess-1.jsonl"})
    log = _log(tmp_path)
    assert "PreCompact: allowing auto compaction session=sess-1 [/proj]" in log


def test_manual_compaction_is_logged_and_allowed(tmp_path):
    _run(tmp_path, {"session_id": "sess-2", "trigger": "manual"})
    assert "allowing manual compaction session=sess-2" in _log(tmp_path)


def test_session_id_falls_back_to_transcript_name(tmp_path):
    _run(tmp_path, {"transcript_path": "/x/abc-123.jsonl", "trigger": "auto"})
    assert "session=abc-123" in _log(tmp_path)


def test_garbage_stdin_does_not_raise(tmp_path):
    state = tmp_path / "askr_state"
    state.mkdir()
    with patch.object(pre_compact, "get_state_dir", return_value=str(state)), \
         patch("askr.session.monitor.find_project_root", return_value="/proj"), \
         patch.object(sys, "stdin", io.StringIO("not json")):
        pre_compact.main()
    assert "session=?" in _log(tmp_path)


def test_no_state_dir_does_nothing(tmp_path):
    _run(tmp_path, {"session_id": "s", "trigger": "auto"}, state_exists=False)
    assert _log(tmp_path) == ""


def test_log_write_failure_never_raises():
    with patch.object(pre_compact, "_DAEMON_LOG_PATH", "/definitely/not/here/daemon.log"):
        pre_compact._log_compaction("s", "auto", "/proj")
