import json
import os
from unittest.mock import patch

from askr.voice import daemon, loop, terminal


def test_status_file_shows_state_partial_and_last_heard(tmp_path):
    clock = [100.0]
    s = daemon.StatusFile(str(tmp_path / "status.json"), clock=lambda: clock[0])
    s.status("hearing…", 0.03, 0.01, "askr run the")
    s.line("ignored", "  heard: thanks for watching   ← no wake word, ignored")
    data = json.loads((tmp_path / "status.json").read_text())
    assert data["state"] == "hearing…" and data["partial"] == "askr run the"
    assert data["last"]["kind"] == "ignored"
    heard = [json.loads(l) for l in open(daemon.HEARD_PATH)]
    assert heard == [{"ts": 100.0, "text": "thanks for watching", "accepted": False}]


def test_status_writes_are_throttled_but_lines_are_immediate(tmp_path):
    clock = [0.0]
    path = tmp_path / "status.json"
    s = daemon.StatusFile(str(path), clock=lambda: clock[0])
    s.status("listening")
    s.status("hearing…")  # within 0.25s: not written
    assert json.loads(path.read_text())["state"] == "listening"
    s.line("you", "run the tests")
    assert json.loads(path.read_text())["state"] == "hearing…"


def _session(sid, pid):
    os.makedirs(terminal._PIDS_DIR, exist_ok=True)
    with open(os.path.join(terminal._PIDS_DIR, sid), "w") as f:
        f.write(str(pid))


def test_target_is_the_focused_claude_terminal(tmp_path):
    _session("aaa", 111)
    _session("bbb", 222)
    paths = {"aaa": str(tmp_path / "aaa.jsonl"), "bbb": str(tmp_path / "bbb.jsonl")}
    for p in paths.values():
        open(p, "w").close()
    os.utime(paths["aaa"], (1, 1))  # bbb is the more recently active one
    daemon._write_json(daemon.FOCUS_PATH, {"shell_pid": 999})
    with patch.object(terminal.os, "kill"), \
         patch.object(daemon, "_ancestors", side_effect=lambda pid: {111: [111, 999], 222: [222, 5]}[pid]), \
         patch.object(daemon, "transcript_for", side_effect=lambda sid: paths[sid]):
        assert daemon.target_transcript() == paths["aaa"]
        daemon._write_json(daemon.FOCUS_PATH, {"shell_pid": 12345})  # a plain shell is focused
        assert daemon.target_transcript() == paths["bbb"]


def test_dead_sessions_are_never_targets(tmp_path):
    _session("gone", 2 ** 22 + 7)
    assert daemon.live_sessions() == {}
    assert daemon.target_transcript() == ""


def test_only_one_daemon_holds_the_lock():
    first = daemon.acquire_lock()
    assert first is not None
    try:
        assert daemon.acquire_lock() is None
        assert daemon.running_pid() == os.getpid()
    finally:
        first.close()


def test_off_disables_and_daemon_then_refuses_to_start(capsys):
    with patch.object(daemon, "stop") as stop:
        loop.main(["off"])
    stop.assert_called_once()
    assert os.path.exists(daemon.DISABLED_PATH)
    with patch.object(daemon.subprocess, "Popen") as popen:
        assert daemon.start_detached() is False
        loop.main(["--daemon"])  # returns immediately
    popen.assert_not_called()
    with patch.object(daemon.subprocess, "Popen") as popen:
        loop.main(["on"])
    assert not os.path.exists(daemon.DISABLED_PATH)
    popen.assert_called_once()
    assert popen.call_args[0][0][-2:] == ["voice", "--daemon"]


def test_clips_are_kept_and_pruned(tmp_path):
    import numpy as np
    clock = [0.0]
    s = daemon.StatusFile(str(tmp_path / "status.json"), clock=lambda: clock[0])
    with patch.object(daemon, "_CLIPS_KEEP", 2):
        for i in range(3):
            clock[0] = 1000.0 + i
            s.save_clip(np.zeros(160), f"text {i}")
    names = sorted(os.listdir(daemon.CLIPS_DIR))
    assert names == ["1001.00.npy", "1001.00.txt", "1002.00.npy", "1002.00.txt"]


def test_stop_kills_a_daemon_that_hangs_on_sigint():
    import subprocess, sys, time
    # A child that ignores SIGINT, standing in for a daemon stuck closing its mic stream.
    child = subprocess.Popen([sys.executable, "-c",
                              "import signal,time; signal.signal(signal.SIGINT, signal.SIG_IGN); time.sleep(60)"])
    try:
        time.sleep(0.3)
        with open(daemon.PID_PATH, "w") as f:
            f.write(str(child.pid))
        assert daemon.stop(wait_secs=0.5) is True
        assert child.wait(timeout=3) == -9
    finally:
        if child.poll() is None:
            child.kill()
