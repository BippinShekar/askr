import json
from unittest.mock import patch

from askr.voice import menu, terminal
from askr.voice.menu import DOWN, ENTER
from askr.voice.talker import Reply

from tests.test_voice_loop import _loop

Q_WAKE = {"question": "Which wake word should replace 'askr'?", "multiSelect": False,
          "options": [{"label": "Nova (Recommended)"}, {"label": "Atlas"},
                      {"label": "Computer"}, {"label": "Keep askr too"}]}
Q_SIZE = {"question": "Pick a size", "multiSelect": False,
          "options": [{"label": "Small"}, {"label": "Medium"}, {"label": "Large"}]}


def _ask(qs, tid="t1"):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": tid, "name": "AskUserQuestion", "input": {"questions": qs}}]}}


def _result(tid="t1"):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tid}]}}


def test_pending_only_until_answered():
    assert menu.pending_questions([_ask([Q_WAKE])]) == [Q_WAKE]
    assert menu.pending_questions([_ask([Q_WAKE]), _result()]) is None


def test_quick_pick():
    opts = Q_WAKE["options"]
    assert menu.quick_pick("the second one", opts) == 2
    assert menu.quick_pick("option three", opts) == 3
    assert menu.quick_pick("Nova", opts) == 1
    assert menu.quick_pick("go with atlas", opts) == 2
    assert menu.quick_pick("the last one", opts) == 4
    assert menu.quick_pick("the first one", opts) == 1
    assert menu.quick_pick("none of those, something calmer like a name", opts) is None


def test_keys_match_the_live_verified_sequences():
    # 2026-11-01, real Claude Code in a pty: Down+Enter -> option 2;
    # Down×3 + text + Enter -> free text; two questions -> extra Enter to submit.
    color = {"options": [{"label": "Red"}, {"label": "Green"}, {"label": "Blue"}]}
    assert menu.keys_for([color], [{"choice": 2}]) == [DOWN, ENTER]
    assert menu.keys_for([color], [{"other": "Purple"}]) == [DOWN, DOWN, DOWN, "Purple", ENTER]
    assert menu.keys_for([color, Q_SIZE], [{"choice": 2}, {"choice": 3}]) == \
        [DOWN, ENTER, DOWN, DOWN, ENTER, ENTER]


def test_unsafe_menus_are_refused():
    multi = dict(Q_SIZE, multiSelect=True)
    assert menu.keys_for([multi], [{"choice": 1}]) is None
    assert menu.keys_for([Q_SIZE], [{"choice": 9}]) is None
    assert menu.keys_for([Q_WAKE, Q_SIZE], [{"choice": 1}, None]) is None


def test_spoken_answer_drives_the_menu_not_a_prompt(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr the second one", Reply("x", "should not send"),
                                     session_entries=[_ask([Q_WAKE])])
    with patch.object(terminal, "type_keys", return_value=True) as type_keys, \
         patch.object(terminal, "type_prompt") as type_prompt, \
         patch.object(loop, "_claimed", return_value=True):
        loop.handle_utterance(b"audio")
    assert type_keys.call_args[0][1] == [DOWN, ENTER]
    type_prompt.assert_not_called()
    assert talker.seen == []
    assert speaker.said == ["Picking Atlas."]


def test_free_answer_goes_through_the_model(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr none of those, just call it hey claude",
                                     Reply("x"), session_entries=[_ask([Q_WAKE])])
    post = lambda body, *a: {"content": [{"type": "text", "text": json.dumps(
        {"answers": [{"other": "Hey Claude"}], "say": "Going with Hey Claude."})}]}
    talker._post = post
    with patch.object(terminal, "type_keys", return_value=True) as type_keys, \
         patch.object(loop, "_claimed", return_value=True):
        loop.handle_utterance(b"audio")
    assert type_keys.call_args[0][1] == [DOWN] * 4 + ["Hey Claude", ENTER]
    assert speaker.said == ["Going with Hey Claude."]


def test_unrelated_speech_while_menu_open_is_never_typed(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr also make the button purple",
                                     Reply("Sending that over.", "make the button purple"),
                                     session_entries=[_ask([Q_WAKE])])
    talker._post = lambda body, *a: {"content": [{"type": "text", "text": '{"answers": null, "say": ""}'}]}
    with patch.object(terminal, "type_keys") as type_keys, patch.object(loop, "deliver") as deliver:
        loop.handle_utterance(b"audio")
    type_keys.assert_not_called()
    deliver.assert_not_called()
    assert "multiple-choice question" in speaker.said[0]
