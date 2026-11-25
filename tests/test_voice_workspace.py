import json
import os
import threading
import time

from askr.voice import daemon, workspace


def test_describe_orients_the_agent():
    focus = {"workspace": "askr", "folders": [os.path.expanduser("~/Desktop/askr")],
             "terminals": ["askr — claude", "zsh"], "name": "askr — claude"}
    text = workspace.describe(focus, os.path.expanduser("~/Desktop/askr"))
    assert 'window "askr" (~/Desktop/askr)' in text
    assert "active: askr — claude" in text and "runs in ~/Desktop/askr" in text
    assert workspace.describe({}, "") == ""


def test_open_terminal_goes_to_the_last_focused_window_and_waits_for_it():
    daemon._write_json(daemon.FOCUS_PATH, {"ext_pid": 4242})
    seen = {}

    def extension():
        for _ in range(50):
            if os.path.exists(workspace.OPEN_TERMINAL_PATH):
                with open(workspace.OPEN_TERMINAL_PATH) as f:
                    seen.update(json.load(f))
                os.remove(workspace.OPEN_TERMINAL_PATH)   # claimed
                return
            time.sleep(0.05)

    threading.Thread(target=extension).start()
    out = workspace.open_terminal("/tmp/proj", workspace.claude_command("hi there"), name="claude")
    assert out.startswith("opened a terminal")
    assert seen["ext_pid"] == 4242 and seen["command"] == "claude 'hi there'"


def test_unclaimed_request_is_withdrawn():
    t = [0.0]

    def clock():
        t[0] += 10
        return t[0]

    assert workspace.open_terminal("", "", clock=clock).startswith("error")
    assert not os.path.exists(workspace.OPEN_TERMINAL_PATH)
