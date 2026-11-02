from askr.voice import agent
from askr.voice.agent import VoiceAgent


def _reply(*blocks, stop="end_turn"):
    return {"content": list(blocks), "stop_reason": stop}


def test_context_is_loaded_only_through_tools_and_not_kept():
    calls, bodies = [], []
    script = [
        _reply({"type": "tool_use", "id": "a", "name": "session_status", "input": {}}, stop="tool_use"),
        _reply({"type": "text", "text": "It's running the tests."}),
    ]

    def post(body, *a):
        bodies.append(body)
        return script.pop(0)

    handlers = {"session_status": lambda inp: (calls.append("status"), "Turn running: yes ... huge digest")[1]}
    a = VoiceAgent(handlers, post=post)
    turn = a.respond("what's it doing")
    assert turn.say == "It's running the tests." and calls == ["status"]
    # First call: only the user's words — no digest pre-loaded.
    assert bodies[0]["messages"] == [{"role": "user", "content": "what's it doing"}]
    # The tool result reached the model on the second call...
    assert bodies[1]["messages"][-1]["content"][0]["content"] == "Turn running: yes ... huge digest"
    # ...but history keeps only the spoken exchange.
    assert "huge digest" not in str(a.history)


def test_actions_are_recorded_and_noted_in_history():
    script = [
        _reply({"type": "tool_use", "id": "a", "name": "send_to_session",
                "input": {"instruction": "Run the tests."}}, stop="tool_use"),
        _reply({"type": "text", "text": "Sent."}),
    ]
    sent = []
    a = VoiceAgent({"send_to_session": lambda inp: (sent.append(inp["instruction"]), "typed into its terminal")[1]},
                   post=lambda body, *x: script.pop(0))
    turn = a.respond("run the tests")
    assert sent == ["Run the tests."] and turn.actions == [("send_to_session", {"instruction": "Run the tests."})]
    assert "send_to_session" in a.history[-1]["content"]


def test_step_limit_and_unknown_tools_do_not_crash():
    loop_forever = lambda body, *a: _reply({"type": "tool_use", "id": "x", "name": "nope", "input": {}}, stop="tool_use")
    turn = VoiceAgent({}, post=loop_forever).respond("hm")
    assert turn.say == "Done." and len(turn.actions) == agent.MAX_STEPS


def test_open_url_refuses_non_web_urls():
    assert agent.open_url("file:///etc/passwd").startswith("error")
