import json
import os
import queue
import threading
from unittest.mock import patch

from askr.voice import inbox, terminal
from askr.voice.loop import VoiceLoop
from askr.voice.talker import Reply
from askr.voice.wake import WakeGate


class FakeListener:
    def __init__(self):
        self.utterances = queue.Queue()
        self.muted = threading.Event()


class FakeSTT:
    def __init__(self, text):
        self.text = text

    def transcribe(self, audio):
        return self.text


class FakeTalker:
    def __init__(self, reply):
        self.reply = reply
        self.seen = []
        self.updates = []

    def respond(self, utterance, digest):
        self.seen.append((utterance, digest))
        return self.reply

    def narrate(self, update, request):
        return f"spoken: {update}"

    def note_update(self, spoken):
        self.updates.append(spoken)


class FakeSpeaker:
    def __init__(self):
        self.gate = WakeGate()
        self.said = []

    def speak(self, text):
        self.said.append(text)


def _loop(tmp_path, heard, reply, session_entries=None):
    t = tmp_path / "sess-1.jsonl"
    t.write_text("\n".join(json.dumps(e) for e in (session_entries or [])) + "\n")
    talker, speaker = FakeTalker(reply), FakeSpeaker()
    loop = VoiceLoop(str(tmp_path), FakeListener(), FakeSTT(heard), talker, speaker)
    with patch("askr.voice.session.find_latest_transcript", return_value=str(t)):
        loop.retarget(force=True)
    return loop, talker, speaker, t


def test_status_question_is_answered_not_sent(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr what is it doing", Reply("It's running tests."))
    with patch.object(loop, "deliver") as deliver:
        loop.handle_utterance(b"audio")
    assert talker.seen[0][0] == "what is it doing"
    assert speaker.said == ["It's running tests."]
    deliver.assert_not_called()


def test_without_wake_word_nothing_happens(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "what's on youtube", Reply("x", "y"))
    loop.handle_utterance(b"audio")
    assert talker.seen == [] and speaker.said == []


def test_send_is_typed_into_terminal_and_claimed(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr make it purple", Reply("On it.", "Make it purple."))

    def type_and_claim(session_id, text, project):
        assert (session_id, text) == ("sess-1", "Make it purple.")
        return True  # no voice_prompt.json left behind == the extension claimed it

    with patch.object(terminal, "type_prompt", side_effect=type_and_claim):
        loop.handle_utterance(b"audio")
    assert speaker.said == ["On it."]
    assert not inbox.pending("sess-1")


def test_unclaimed_prompt_mid_turn_falls_back_to_inbox(tmp_path):
    running = [{"type": "user", "message": {"content": "do x"}}]
    loop, talker, speaker, _ = _loop(tmp_path, "askr also run lint", Reply("Okay.", "Also run lint."), running)

    def type_never_claimed(session_id, text, project):
        with open(terminal._VOICE_PROMPT_PATH, "w") as f:
            f.write("{}")
        return True

    with patch.object(terminal, "type_prompt", side_effect=type_never_claimed), \
         patch("askr.voice.loop._CLAIM_TIMEOUT_SECS", 0.3):
        loop.handle_utterance(b"audio")
    assert inbox.drain("sess-1") == ["Also run lint."]
    assert not os.path.exists(terminal._VOICE_PROMPT_PATH)  # stale prompt removed
    assert "when it finishes this step" in speaker.said[-1]


def test_no_terminal_when_idle_says_so(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr run tests", Reply("Sure.", "Run the tests."))
    with patch.object(terminal, "type_prompt", return_value=False):
        loop.handle_utterance(b"audio")
    assert not inbox.pending("sess-1")
    assert "couldn't find" in speaker.said[-1]


def test_narration_speaks_turn_end_and_records_it(tmp_path):
    loop, talker, speaker, t = _loop(tmp_path, "", Reply("x"))
    with open(t, "a") as f:
        f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "All tests pass."}]}}) + "\n")
        f.write(json.dumps({"type": "system", "subtype": "turn_duration"}) + "\n")
    loop.narrate()
    assert speaker.said == ["spoken: All tests pass."]
    assert talker.updates == ["spoken: All tests pass."]


def test_pinned_session(tmp_path):
    (tmp_path / "other.jsonl").write_text("")
    (tmp_path / "pinned.jsonl").write_text("")
    loop = VoiceLoop(str(tmp_path), FakeListener(), FakeSTT(""), FakeTalker(Reply("x")), FakeSpeaker(),
                     session_id="pinned")
    with patch("askr.voice.session.find_latest_transcript", return_value=str(tmp_path / "other.jsonl")):
        loop.retarget(force=True)
    assert loop.session_id == "pinned"
