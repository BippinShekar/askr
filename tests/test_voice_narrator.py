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

    def fake_run(cmd, **kw):
        listener.muted_during = listener.muted.is_set()

    with patch("askr.voice.speaker.subprocess.run", side_effect=fake_run) as run, \
         patch("askr.voice.speaker.time.sleep"):
        s.speak("**Tests** pass.")
    assert listener.muted_during is True
    assert not listener.muted.is_set()
    assert gate.opened is not None
    assert run.call_args[0][0][-1] == "Tests pass."  # markdown stripped


def test_speaker_noop_on_empty_text():
    s = Speaker()
    with patch("askr.voice.speaker.subprocess.run") as run:
        s.speak("")
    run.assert_not_called()
