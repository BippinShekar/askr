import json
import queue
import threading
from unittest.mock import patch

from askr.voice import notes
from askr.voice.loop import VoiceLoop
from askr.voice.talker import Reply
from askr.voice.wake import WakeGate


class _Listener:
    def __init__(self):
        self.utterances = queue.Queue()
        self.muted = threading.Event()


class _STT:
    def __init__(self):
        self.text = ""

    def transcribe(self, audio):
        return self.text


class _Talker:
    def __init__(self):
        self.seen = []

    def respond(self, utterance, digest):
        self.seen.append(utterance)
        return Reply("ok", "should not be sent")


class _Speaker:
    def __init__(self):
        self.gate = WakeGate()
        self.said = []

    def speak(self, text):
        self.said.append(text)


def test_start_and_stop_phrases():
    for said in ["Can you transcribe whatever I'm saying onto the Notes app?",
                 "take notes", "dictate this into Notes", "write what I say in notes"]:
        assert notes.wants_start(said), said
    for said in ["what's in the release notes section of the PR", "run the tests", "stop taking notes"]:
        assert not notes.wants_start(said), said
    for said in ["Stop taking notes.", "okay, end the dictation", "I'm done with notes"]:
        assert notes.wants_stop(said), said
    assert not notes.wants_stop("note that the stop button is red")


def test_dictation_mode_end_to_end(tmp_path):
    scripts = []
    stt, talker, speaker = _STT(), _Talker(), _Speaker()
    loop = VoiceLoop(str(tmp_path), _Listener(), stt, talker, speaker)
    with patch.object(notes, "_osascript", side_effect=lambda s: scripts.append(s) or True):
        stt.text = "Askr, can you transcribe whatever I'm saying onto the Notes app?"
        loop.handle_utterance(b"a")
        assert notes.active() and "Taking notes" in speaker.said[0]
        stt.text = 'First idea: "pricing" & tiers.'   # no wake word needed now
        loop.handle_utterance(b"a")
        stt.text = "Stop taking notes."
        loop.handle_utterance(b"a")
    assert notes.active() is None
    assert talker.seen == []                      # nothing went to Claude
    assert "make new note" in scripts[0]
    assert '<div>First idea: &quot;pricing&quot; &amp; tiers.</div>' in scripts[1].replace('\\"', '"')
    assert len(scripts) == 2                      # the stop phrase isn't written into the note


def test_dictation_turns_itself_off_when_idle():
    with patch.object(notes, "_osascript", return_value=True):
        notes.start(now=1000.0)
    assert notes.active(now=1000.0 + notes.IDLE_SECS - 1)
    assert notes.active(now=1000.0 + notes.IDLE_SECS + 1) is None
    assert notes.active() is None  # and it stays off


def test_wake_word_lines_are_commands_even_while_dictating(tmp_path):
    stt, talker, speaker = _STT(), _Talker(), _Speaker()
    loop = VoiceLoop(str(tmp_path), _Listener(), stt, talker, speaker)
    with patch.object(notes, "_osascript", return_value=True) as osa:
        notes.start()
        osa.reset_mock()
        stt.text = "Askr, stop taking notes."
        loop.handle_utterance(b"a")
    assert notes.active() is None
    osa.assert_not_called()  # not written into the note
