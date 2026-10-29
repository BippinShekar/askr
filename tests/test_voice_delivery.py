import contextlib
import io
import json
import os
import sys
from unittest.mock import patch

from askr.hooks import stop
from askr.voice import inbox, terminal


# --- inbox -------------------------------------------------------------------

def test_post_then_drain_in_order_and_empties():
    inbox.post("s1", "first")
    inbox.post("s1", "second")
    assert inbox.pending("s1")
    assert inbox.drain("s1") == ["first", "second"]
    assert not inbox.pending("s1")
    assert inbox.drain("s1") == []


def test_inboxes_are_per_session():
    inbox.post("a", "for a")
    assert inbox.drain("b") == []
    assert inbox.drain("a") == ["for a"]


def test_drain_without_session_id():
    assert inbox.drain("") == []


def test_as_context_lists_messages():
    text = inbox.as_context(["skip the flaky test", "then commit"])
    assert "by voice" in text and "- skip the flaky test\n- then commit" in text


# --- Stop --------------------------------------------------------------------

def _run_stop(tmp_path, session_id):
    state = tmp_path / "askr_state"
    state.mkdir(exist_ok=True)
    buf = io.StringIO()
    payload = json.dumps({"session_id": session_id, "transcript_path": ""})
    with patch.object(stop, "get_state_dir", return_value=str(state)), \
         patch.object(stop, "load_developer", return_value="dev"), \
         patch.object(stop, "_update_allowed_tools", side_effect=SystemExit), \
         patch.object(sys, "stdin", io.StringIO(payload)), \
         contextlib.redirect_stdout(buf):
        try:
            stop.main()
        except SystemExit:
            pass  # stop the rest of stop.main(); only the voice block is under test
    return buf.getvalue()


def test_stop_blocks_with_unread_voice_input(tmp_path):
    inbox.post("s5", "and push it")
    data = json.loads(_run_stop(tmp_path, "s5"))
    assert data["decision"] == "block"
    assert "- and push it" in data["reason"]
    assert not inbox.pending("s5")


def test_stop_silent_without_voice_input(tmp_path):
    assert _run_stop(tmp_path, "s6") == ""


# --- terminal ----------------------------------------------------------------

def _fake_ps(tree):
    class R:
        def __init__(self, out):
            self.stdout = out

    def run(cmd, **kwargs):
        pid = int(cmd[-1])
        ppid, comm = tree.get(pid, (None, None))
        return R(f" {ppid} {comm}\n" if ppid is not None else "")
    return run


def test_record_own_pid_finds_claude_ancestor():
    tree = {500: (400, "/bin/sh"), 400: (300, "claude")}
    with patch.object(terminal.os, "getppid", return_value=500), \
         patch.object(terminal.subprocess, "run", side_effect=_fake_ps(tree)):
        terminal.record_own_pid("s7")
    with open(os.path.join(terminal._PIDS_DIR, "s7")) as f:
        assert f.read() == "400"


def test_record_own_pid_without_claude_ancestor_writes_nothing():
    tree = {500: (1, "/bin/sh")}
    with patch.object(terminal.os, "getppid", return_value=500), \
         patch.object(terminal.subprocess, "run", side_effect=_fake_ps(tree)):
        terminal.record_own_pid("s8")
    assert not os.path.exists(os.path.join(terminal._PIDS_DIR, "s8"))


def test_type_prompt_writes_ancestor_pids():
    os.makedirs(terminal._PIDS_DIR, exist_ok=True)
    with open(os.path.join(terminal._PIDS_DIR, "s9"), "w") as f:
        f.write(str(os.getpid()))  # a live pid
    with patch("askr.session.lifecycle._get_ancestor_pids", return_value=[11, 22]):
        assert terminal.type_prompt("s9", "run the tests", "/proj") is True
    with open(terminal._VOICE_PROMPT_PATH) as f:
        p = json.load(f)
    assert p["text"] == "run the tests"
    assert p["ancestor_pids"] == [os.getpid(), 11, 22]


def test_type_prompt_dead_session_returns_false():
    os.makedirs(terminal._PIDS_DIR, exist_ok=True)
    with open(os.path.join(terminal._PIDS_DIR, "s10"), "w") as f:
        f.write("999999")
    assert terminal.type_prompt("s10", "x") is False
