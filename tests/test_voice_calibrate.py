import io
import queue

import numpy as np
from unittest.mock import patch

from askr.voice import calibrate, wake
from askr.voice.listener import FRAME_SAMPLES
from askr.voice.ui import Display, meter


def test_speech_rms_ignores_silence_around_word():
    rng = np.random.default_rng(0)
    quiet = rng.standard_normal(FRAME_SAMPLES * 30) * 0.001
    loud = rng.standard_normal(FRAME_SAMPLES * 10) * 0.05
    level = calibrate.speech_rms(np.concatenate([quiet, loud, quiet]).astype(np.float32))
    assert 0.03 < level < 0.07


def test_floor_is_quarter_of_quietest_attempt_within_bounds():
    assert calibrate.floor_for([0.02, 0.012]) == 0.003
    assert calibrate.floor_for([0.0001]) == 0.0015   # never below
    assert calibrate.floor_for([0.2]) == 0.01        # never above
    assert calibrate.floor_for([]) == 0.004


def test_heard_variant():
    assert calibrate.heard_variant("Is car.") == ["is", "iscar"]
    assert calibrate.heard_variant("Asgaard") == ["asgaard"]
    assert calibrate.heard_variant("") == []


class FakeMic:
    def __init__(self, segmenter=None):
        self.segmenter = segmenter
        self.utterances = queue.Queue()
        for _ in range(3):
            self.utterances.put(np.full(FRAME_SAMPLES * 10, 0.02, dtype=np.float32))

    def start(self):
        pass

    def stop(self):
        pass


class FakeSTT:
    def __init__(self, outputs):
        self.outputs = list(outputs)

    def transcribe(self, audio):
        return self.outputs.pop(0)


def test_run_learns_unknown_spelling_and_saves_floor():
    out = io.StringIO()
    with patch.object(calibrate, "MicListener", FakeMic), \
         patch.object(calibrate, "_WAIT_SECS", 0.3):
        profile = calibrate.run(FakeSTT(["Asgir.", "Askr.", "Asgir"]), Display(out), rounds=3)
    assert profile["variants"] == ["asgir"]            # known "Askr" not learned
    assert abs(profile["min_rms"] - calibrate.floor_for([0.02])) < 1e-6
    assert wake.load_profile()["variants"] == ["asgir"]
    assert "recognised" in out.getvalue() and "learned 'asgir'" in out.getvalue()


def test_run_with_silent_mic_reports_permission_hint():
    class SilentMic(FakeMic):
        def __init__(self, segmenter=None):
            self.segmenter = segmenter
            self.utterances = queue.Queue()

    out = io.StringIO()
    with patch.object(calibrate, "MicListener", SilentMic), \
         patch.object(calibrate, "_WAIT_SECS", 0.2):
        profile = calibrate.run(FakeSTT([]), Display(out), rounds=2)
    assert "min_rms" not in profile
    assert "Microphone" in out.getvalue()


def test_meter_marks_threshold_and_fills_with_level():
    bar = meter(0.05, 0.01)
    assert "|" in bar and bar.startswith("▮")
    assert set(meter(0.0, 0.01)) <= {"·", "|"}


def test_learnable_rejects_common_and_unlike_words():
    for word in ["you", "the", "asked", "okay", "hello", "banana", "a"]:
        assert not calibrate.learnable(word), word
    for word in ["asgir", "iscar", "eskar", "askir"]:
        assert calibrate.learnable(word), word


def _mic_with(n):
    class Mic(FakeMic):
        def __init__(self, segmenter=None):
            self.segmenter = segmenter
            self.utterances = queue.Queue()
            for _ in range(n):
                self.utterances.put(np.full(FRAME_SAMPLES * 10, 0.02, dtype=np.float32))
    return Mic


def test_background_sentences_are_not_samples_and_video_cannot_calibrate():
    # The 2026-10-30 failure: a YouTube video in the background "calibrated" it
    # and taught it "you". Sentences don't count; too few samples isn't saved.
    out = io.StringIO()
    stt = FakeSTT(["I will see you in the next video.", "you", "Thanks for watching everyone!",
                   "Askr.", "So that is how it works.", "you"])
    with patch.object(calibrate, "MicListener", _mic_with(6)), \
         patch.object(calibrate, "_WAIT_SECS", 0.2):
        profile = calibrate.run(stt, Display(out), rounds=3)
    assert "calibrated_at" not in profile
    assert "you" not in profile.get("variants", [])
    assert wake.load_profile() == {}
    assert "not saved" in out.getvalue()
