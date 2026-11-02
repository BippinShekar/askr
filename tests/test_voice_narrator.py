import json
from unittest.mock import patch

from askr.voice.narrator import Narrator
from askr.voice.speaker import Speaker


def _append(path, *entries, newline=True):
    with open(path, "a") as f:
        for e in entries:
            f.write(json.dumps(e) + ("\n" if newline else ""))


def _text(t):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}


END = {"type": "system", "subtype": "turn_duration"}


def test_ignores_history_before_start(tmp_path):
    p = tmp_path / "t.jsonl"
    _append(p, _text("old answer"), END)
    n = Narrator(str(p))
    assert n.poll(now=0) == []


def test_turn_end_speaks_final_message(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("")
    n = Narrator(str(p))
    _append(p, _text("Looking into it."), _text("Fixed, tests pass."), END)
    events = n.poll(now=1)
    assert [(e.kind, e.text) for e in events] == [("done", "Fixed, tests pass.")]


def test_question_is_spoken(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("")
    n = Narrator(str(p))
    _append(p, {"type": "assistant", "message": {"content": [{
        "type": "tool_use", "name": "AskUserQuestion",
        "input": {"questions": [{"question": "Which database?"}]}}]}})
    assert [(e.kind, e.text) for e in n.poll(now=1)] == [("question", "Which database?")]


def test_progress_is_throttled(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("")
    n = Narrator(str(p), progress_every=90)
    _append(p, _text("Step one done."))
    assert [e.kind for e in n.poll(now=100)] == ["progress"]
    _append(p, _text("Step two done."))
    assert n.poll(now=150) == []                       # within 90s of last speech
    assert [e.text for e in n.poll(now=191)] == ["Step two done."]
    assert n.poll(now=400) == []                       # nothing new, nothing said


def test_partial_line_is_completed_next_poll(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("")
    n = Narrator(str(p))
    line = json.dumps(_text("Done.")) + "\n" + json.dumps(END) + "\n"
    with open(p, "a") as f:
        f.write(line[:20])
    assert n.poll(now=1) == []
    with open(p, "a") as f:
        f.write(line[20:])
    assert [e.text for e in n.poll(now=2)] == ["Done."]


def test_mark_spoken_resets_progress_throttle(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text("")
    n = Narrator(str(p), progress_every=90)
    n.mark_spoken(now=100)
    _append(p, _text("Working."))
    assert n.poll(now=150) == []
    assert [e.kind for e in n.poll(now=191)] == ["progress"]


# --- Speaker -----------------------------------------------------------------

class _FakeListener:
    def __init__(self):
        import threading
        self.muted = threading.Event()
        self.muted_during = None


class _FakeGate:
    opened = None

    def open_window(self, now):
        self.opened = now


def test_speaker_mutes_mic_while_speaking_then_opens_window():
    listener, gate = _FakeListener(), _FakeGate()
    s = Speaker(listener=listener, gate=gate)
    s.say_bin = "/usr/bin/say"

    class FakeProc:
        def __init__(self, cmd):
            self.cmd = cmd
            listener.muted_during = listener.muted.is_set()

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0

    with patch("askr.voice.speaker.subprocess.Popen", side_effect=FakeProc) as popen, \
         patch("askr.voice.speaker.time.sleep"):
        s.speak("**Tests** pass.")
    assert listener.muted_during is True
    assert not listener.muted.is_set()
    assert gate.opened is not None
    assert popen.call_args[0][0][-1] == "Tests pass."  # markdown stripped


def test_muted_askr_says_nothing_anywhere():
    # ⌘M silences voice mode and every other spoken output (notifications too).
    import os
    from askr.clients import voice
    os.makedirs(os.path.dirname(voice.MUTED_PATH), exist_ok=True)
    open(voice.MUTED_PATH, "w").close()
    s = Speaker()
    s.say_bin = "/usr/bin/say"
    with patch("askr.voice.speaker.subprocess.Popen") as popen:
        s.speak("hello")
    popen.assert_not_called()
    assert voice._say_preconditions() == ("", "askr is muted (⌘M)")


def test_stop_cuts_off_current_speech():
    s = Speaker()

    class Proc:
        terminated = False

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

    s._proc = Proc()
    s.stop()
    assert s._proc.terminated


def test_speaker_noop_on_empty_text():
    s = Speaker()
    with patch("askr.voice.speaker.subprocess.run") as run:
        s.speak("")
    run.assert_not_called()
