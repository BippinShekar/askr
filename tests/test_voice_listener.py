import numpy as np

from askr.voice.listener import FRAME_SAMPLES, Segmenter
from askr.voice.wake import WakeGate


def _frames(level, n, seed=0):
    rng = np.random.default_rng(seed)
    return [(rng.standard_normal(FRAME_SAMPLES) * level).astype(np.float32) for _ in range(n)]


def _feed(seg, frames):
    return [u for u in (seg.feed(f) for f in frames) if u is not None]


# --- Segmenter ---------------------------------------------------------------

def test_speech_between_silence_yields_one_utterance():
    seg = Segmenter()
    out = _feed(seg, _frames(0.001, 50) + _frames(0.1, 40, 1) + _frames(0.001, 40, 2))
    assert len(out) == 1
    # Speech plus preroll plus trailing silence, all in one buffer.
    assert len(out[0]) >= 40 * FRAME_SAMPLES


def test_silence_only_yields_nothing():
    assert _feed(Segmenter(), _frames(0.001, 300)) == []


def test_short_click_is_dropped():
    seg = Segmenter()
    assert _feed(seg, _frames(0.001, 50) + _frames(0.1, 4, 1) + _frames(0.001, 40, 2)) == []


def test_noise_floor_adapts_to_loud_room():
    # Steady fan noise well above min_rms must not register as speech.
    seg = Segmenter()
    assert _feed(seg, _frames(0.02, 400)) == []


def test_max_length_cuts_runaway_utterance():
    seg = Segmenter(max_ms=3000)
    out = _feed(seg, _frames(0.001, 50) + _frames(0.1, 300, 1))
    assert len(out) >= 2


def test_two_utterances_separated_by_pause():
    seg = Segmenter()
    out = _feed(seg, _frames(0.001, 50) + _frames(0.1, 30, 1) + _frames(0.001, 40, 2)
                + _frames(0.1, 30, 3) + _frames(0.001, 40, 4))
    assert len(out) == 2


# --- WakeGate ----------------------------------------------------------------

def test_wake_word_variants_are_stripped():
    for said in ["Askr, run the tests", "Asker run the tests", "Ask her, run the tests",
                 "hey askr run the tests", "Okay Oscar, run the tests",
                 "Askr. Run the tests", "He askedr. Run the tests", "He asked her, run the tests",
                 "He askr, run the tests"]:
        assert WakeGate().accept(said, now=0).lower() == "run the tests", said


def test_without_wake_word_is_ignored():
    assert WakeGate().accept("run the tests", now=0) is None


def test_follow_up_window_after_accept():
    gate = WakeGate(follow_up_secs=20)
    assert gate.accept("askr what's the status", now=0) == "what's the status"
    assert gate.accept("and push it", now=10) == "and push it"
    assert gate.accept("and push it", now=31) is None  # window from t=10 ended at 30


def test_open_window_after_speaking():
    gate = WakeGate(follow_up_secs=20)
    gate.open_window(now=100)
    assert gate.accept("yes do that", now=115) == "yes do that"


def test_bare_wake_word_opens_window_without_command():
    gate = WakeGate()
    assert gate.accept("Askr.", now=0) is None
    assert gate.accept("check the build", now=5) == "check the build"


def test_whisper_noise_hallucinations_ignored_even_in_window():
    gate = WakeGate()
    gate.open_window(now=0)
    for noise in ["Thank you.", "you", " Thanks for watching!", ""]:
        assert gate.accept(noise, now=1) is None


def test_wake_word_must_be_at_start():
    assert WakeGate().accept("I was telling my friend to ask her later", now=0) is None
