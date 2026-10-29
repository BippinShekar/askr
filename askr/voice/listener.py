"""
Mic -> utterances. Energy-based segmentation with an adaptive noise floor:
cheap, no extra model, and Whisper's own VAD filter (stt.py) drops whatever
non-speech slips through. The mic is ignored while `muted` is set — askr
mutes it while `say` is talking so it never transcribes itself.
"""

import collections
import queue
import threading

import numpy as np

SAMPLE_RATE = 16_000
FRAME_MS = 30
FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS // 1000


class Segmenter:
    """
    Feed fixed-size float32 frames; returns a finished utterance (np.ndarray)
    when one ends, else None. Pure — no audio I/O — so it's unit-testable.
    """

    def __init__(self, start_ratio: float = 3.0, min_rms: float = 0.004,
                 start_frames: int = 3, end_silence_ms: int = 800,
                 preroll_ms: int = 600, max_ms: int = 30_000, min_speech_ms: int = 300):
        self.start_ratio = start_ratio
        self.min_rms = min_rms
        self.start_frames = start_frames
        self.end_frames = end_silence_ms // FRAME_MS
        self.max_frames = max_ms // FRAME_MS
        self.min_speech_frames = min_speech_ms // FRAME_MS
        self.noise = min_rms
        self._preroll = collections.deque(maxlen=preroll_ms // FRAME_MS)
        self._frames = []
        self._loud_run = 0
        self._silent_run = 0
        self._speech_frames = 0
        self.active = False

    def _threshold(self) -> float:
        return max(self.min_rms, self.noise * self.start_ratio)

    def feed(self, frame: np.ndarray):
        rms = float(np.sqrt(np.mean(frame * frame))) if frame.size else 0.0
        loud = rms > self._threshold()

        if not self.active:
            # Track the room's noise floor only while nobody is talking.
            if not loud:
                self.noise = 0.95 * self.noise + 0.05 * max(rms, 1e-5)
            self._preroll.append(frame)
            self._loud_run = self._loud_run + 1 if loud else 0
            if self._loud_run >= self.start_frames:
                self.active = True
                self._frames = list(self._preroll)
                self._speech_frames = self._loud_run
                self._silent_run = 0
            return None

        self._frames.append(frame)
        if loud:
            self._speech_frames += 1
            self._silent_run = 0
        else:
            self._silent_run += 1
        if self._silent_run >= self.end_frames or len(self._frames) >= self.max_frames:
            return self._finish()
        return None

    def _finish(self):
        frames, speech = self._frames, self._speech_frames
        self.reset()
        if speech < self.min_speech_frames:
            return None
        return np.concatenate(frames)

    def reset(self):
        self.active = False
        self._frames = []
        self._preroll.clear()
        self._loud_run = self._silent_run = self._speech_frames = 0


class MicListener:
    """Runs the mic on a sounddevice callback thread; utterances land on `.utterances`."""

    def __init__(self, segmenter: Segmenter | None = None, device=None):
        self.segmenter = segmenter or Segmenter()
        self.device = device
        self.utterances: "queue.Queue[np.ndarray]" = queue.Queue()
        self.muted = threading.Event()
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if self.muted.is_set():
            if self.segmenter.active:
                self.segmenter.reset()
            return
        utterance = self.segmenter.feed(indata[:, 0].astype(np.float32, copy=True))
        if utterance is not None:
            self.utterances.put(utterance)

    def start(self):
        import sounddevice as sd
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32",
            blocksize=FRAME_SAMPLES, callback=self._callback, device=self.device,
        )
        self._stream.start()

    def stop(self):
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
