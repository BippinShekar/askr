import json

from askr.voice import session
from askr.voice.talker import Talker, _parse


def _write(tmp_path, entries):
    p = tmp_path / "s.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
    return str(p)


def _user(text):
    return {"type": "user", "message": {"content": text}}


def _assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


TURN_END = {"type": "system", "subtype": "turn_duration"}


# --- digest ------------------------------------------------------------------

def test_digest_finished_turn(tmp_path):
    path = _write(tmp_path, [
        _user("fix the login bug"),
        _assistant({"type": "tool_use", "name": "Bash", "input": {"command": "npm test"}}),
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
        _assistant({"type": "text", "text": "Fixed it, tests pass."}),
        TURN_END,
        {"type": "system", "subtype": "away_summary"},
    ])
    d = session.digest(path)
    assert d.in_flight is False
    assert d.last_prompt == "fix the login bug"
    assert d.recent_tools == ["Bash: npm test"]
    assert d.recent_text == ["Fixed it, tests pass."]
    assert "waiting for the user" in d.render()


def test_digest_turn_in_flight(tmp_path):
    path = _write(tmp_path, [
        _user("old"), TURN_END,
        _user("run the migration"),
        _assistant({"type": "tool_use", "name": "Bash", "input": {"description": "Run migration"}}),
    ])
    d = session.digest(path)
    assert d.in_flight is True
    assert d.last_prompt == "run the migration"
    assert d.recent_tools[-1] == "Bash: Run migration"


def test_digest_ignores_meta_and_tool_results_as_prompts(tmp_path):
    path = _write(tmp_path, [
        _user("real prompt"),
        {"type": "user", "isMeta": True, "message": {"content": "Caveat: injected"}},
        _user("<command-name>/clear</command-name>"),
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "x"}]}},
    ])
    assert session.digest(path).last_prompt == "real prompt"


def test_digest_missing_file():
    d = session.digest("/nonexistent.jsonl")
    assert d.in_flight is False and d.last_prompt == ""


def test_find_latest_transcript(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    folder = tmp_path / ".claude" / "projects" / "-Users-me-my-proj"
    folder.mkdir(parents=True)
    old, new = folder / "a.jsonl", folder / "b.jsonl"
    old.write_text("{}")
    new.write_text("{}")
    import os
    os.utime(old, (1, 1))
    assert session.find_latest_transcript("/Users/me/my_proj") == str(new)


# --- talker ------------------------------------------------------------------

def test_parse_valid_json():
    r = _parse('{"say": "On it.", "send": "Run the lint"}')
    assert r.say == "On it." and r.send == "Run the lint"


def test_parse_json_wrapped_in_prose():
    r = _parse('Sure:\n{"say": "It is running tests.", "send": null}\n')
    assert r.say == "It is running tests." and r.send is None


def test_instruction_is_always_sent_even_if_model_withholds_it():
    r = _parse('{"intent": "instruction", "send": null, '
               '"say": "Did you mean a different session?"}', "make the archived layer purple")
    assert r.send == "make the archived layer purple"
    assert r.say == "Sending that over."


def test_instruction_keeps_models_cleaned_send_and_confirmation():
    r = _parse('{"intent": "instruction", "send": "Make the archived layer purple.", '
               '"say": "Passing that on."}', "tell it to make the archive layer purple")
    assert r.send == "Make the archived layer purple." and r.say == "Passing that on."


def test_clarify_is_not_forced_through():
    r = _parse('{"intent": "clarify", "send": null, "say": "The colour of what?"}', "change the colour")
    assert r.send is None and r.say == "The colour of what?"


def test_parse_garbage_falls_back():
    r = _parse("no json here")
    assert r.send is None and "didn't get" in r.say


def _fake_post(reply_json, calls):
    def post(body, mode, preview):
        calls.append(body)
        return {"content": [{"type": "text", "text": reply_json}]}
    return post


def test_respond_sends_digest_and_keeps_spoken_history_only():
    calls = []
    t = Talker(post=_fake_post('{"say": "Passing it on.", "send": "Also run lint"}', calls))
    r = t.respond("also run the link", "Turn running: yes")
    assert r.send == "Also run lint"
    assert "Turn running: yes" in calls[0]["messages"][-1]["content"]
    assert calls[0]["model"] == "claude-haiku-4-5-20251001"
    t.respond("thanks", "Turn running: no")
    # Second call carries prior spoken turns but not the stale first digest.
    second = calls[1]["messages"]
    assert second[0] == {"role": "user", "content": "also run the link"}
    assert all("Turn running: yes" not in m["content"] for m in second)


def test_history_is_capped():
    calls = []
    t = Talker(post=_fake_post('{"say": "ok", "send": null}', calls))
    for i in range(20):
        t.respond(f"u{i}", "d")
    assert len(t.history) == 12


def test_respond_survives_transport_error():
    def boom(*a):
        raise RuntimeError("HTTP 500")
    r = Talker(post=boom).respond("hello", "d")
    assert r.send is None and "couldn't reach" in r.say
