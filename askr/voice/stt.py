"""
Local speech-to-text via faster-whisper. Audio never leaves the machine; the
model (~140 MB for base.en) downloads once to the Hugging Face cache.
"""

import numpy as np

DEFAULT_MODEL = "base.en"


class Transcriber:
    def __init__(self, model: str = DEFAULT_MODEL):
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model, device="cpu", compute_type="int8")

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio, language="en", beam_size=1, vad_filter=True,
            condition_on_previous_text=False,
            # Primes Whisper to keep the unfamiliar wake word at the start of a
            # sentence. Measured 2026-10-29 on base.en: a bare "Askr." prompt
            # dropped the wake word on 2 of 4 test sentences, this one on 0 of 4.
            initial_prompt="Askr, run the tests.",
        )
        return " ".join(s.text.strip() for s in segments).strip()
