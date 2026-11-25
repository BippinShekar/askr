from askr.voice.addressee import MAX_CHECKS_PER_MIN, Addressee
from askr.voice.talker import Reply

from tests.test_voice_loop import _loop


def _yes_no(answer, calls):
    def post(body, *a):
        calls.append(body["messages"][0]["content"])
        return {"content": [{"type": "text", "text": answer}]}
    return post


def test_filters_before_any_model_call():
    a = Addressee(post=lambda *a: (_ for _ in ()).throw(AssertionError("no call expected")), clock=lambda: 0)
    assert a.worth_checking("you")                                   # Whisper noise
    assert a.worth_checking(" ".join(["blah"] * 60))                 # monologue chunk
    assert a.worth_checking("run the tests") == ""
    assert a.worth_checking("stop") == ""                            # one-word commands count


def test_rate_cap():
    calls = []
    a = Addressee(post=_yes_no("no", calls), clock=lambda: 100.0)
    for _ in range(MAX_CHECKS_PER_MIN):
        assert a.worth_checking("is it done yet") == ""
        a.is_for_askr("is it done yet")
    assert "rate-capped" in a.worth_checking("is it done yet")


def test_always_on_acts_without_wake_word_when_meant_for_it(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "run the tests", Reply("", "Run the tests."))
    calls = []
    loop.addressee = Addressee(post=_yes_no("yes", calls), clock=loop.clock)
    from unittest.mock import patch
    with patch.object(loop, "deliver", return_value="typed into its terminal") as deliver:
        loop.handle_utterance(b"a")
    assert calls and deliver.called


def test_always_on_ignores_background(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "and that's how you make the perfect pasta", Reply("x", "y"))
    loop.addressee = Addressee(post=_yes_no("no", []), clock=loop.clock)
    loop.handle_utterance(b"a")
    assert talker.seen == [] and speaker.said == []


def test_wake_word_skips_the_check(tmp_path):
    loop, talker, speaker, _ = _loop(tmp_path, "askr what's it doing", Reply("Running tests."))
    loop.addressee = Addressee(post=lambda *a: (_ for _ in ()).throw(AssertionError("no check")), clock=loop.clock)
    loop.handle_utterance(b"a")
    assert talker.seen[0][0] == "what's it doing"
