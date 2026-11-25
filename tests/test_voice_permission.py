import json
from unittest.mock import patch

from askr.voice import events, permission, terminal
from askr.voice.menu import DOWN, ENTER
from askr.voice.talker import Reply

from tests.test_voice_loop import _loop

BASH = {"type": "assistant", "message": {"content": [
    {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "npm test", "description": "npm test"}}]}}
RESULT = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}}


def test_classify_plain_answers():
    for said, want in [("yes", "yes"), ("yeah go ahead", "yes"), ("sure, run it", "yes"),
                       ("yes, always", "always"), ("don't ask again", "always"),
                       ("no", "no"), ("nah don't", "no"), ("wait", "no"),
                       ("what is it trying to do", None), ("make the header purple", None)]:
        assert permission.classify(said) == want, said


def test_describe_and_pending():
    assert permission.pending_tool([BASH]) ["id"] == "t1"
    assert permission.pending_tool([BASH, RESULT]) is None
    assert permission.describe(BASH["message"]["content"][0]) == "run npm test"


def _with_prompt(tmp_path, heard):
    loop, talker, speaker, t = _loop(tmp_path, heard, Reply("x", "should not send"), session_entries=[BASH])
    events.post(loop.session_id, "permission_prompt", "Claude needs your permission to use Bash", str(tmp_path))
    loop.speak_events()
    return loop, talker, speaker, t


def test_prompt_is_described_and_a_spoken_yes_approves_it(tmp_path):
    loop, talker, speaker, _ = _with_prompt(tmp_path, "yeah go ahead")
    assert speaker.said == ["It wants to run npm test. OK?"]
    with patch.object(terminal, "type_keys", return_value=True) as keys, \
         patch.object(loop, "_claimed", return_value=True):
        loop.handle_utterance(b"a")        # conversation is open after askr asked: no wake word
    assert keys.call_args[0][1] == [ENTER]
    assert talker.seen == []               # answered directly, nothing sent to Claude


def test_always_and_no(tmp_path):
    loop, *_ = _with_prompt(tmp_path, "yes and don't ask again")
    with patch.object(terminal, "type_keys", return_value=True) as keys, \
         patch.object(loop, "_claimed", return_value=True):
        loop.handle_utterance(b"a")
    assert keys.call_args[0][1] == [DOWN, ENTER]


def test_no_keys_once_it_was_answered_on_screen(tmp_path):
    # The user clicked it themselves: a late "yes" must not type into the prompt,
    # where Down+Enter would re-send their previous message.
    loop, talker, speaker, t = _with_prompt(tmp_path, "yes")
    with open(t, "a") as f:
        f.write(json.dumps(RESULT) + "\n")
    with patch.object(terminal, "type_keys") as keys:
        loop.handle_utterance(b"a")
    keys.assert_not_called()
