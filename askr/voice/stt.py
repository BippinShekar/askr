"""
Local speech-to-text via faster-whisper. Audio never leaves the machine; the
model (~140 MB for base.en) downloads once to the Hugging Face cache.
"""

import numpy as np

DEFAULT_MODEL = "base.en"


class Transcriber:
    def __init__(self, model: str = DEFAULT_MODEL, wake_word: str = "Askr"):
        from faster_whisper import WhisperModel
        self._model = WhisperModel(model, device="cpu", compute_type="int8")
        self._prompt = f"{wake_word[:1].upper()}{wake_word[1:]}, run the tests."

    def transcribe(self, audio: np.ndarray) -> str:
        segments, _ = self._model.transcribe(
            audio, language="en", beam_size=1, vad_filter=True,
            condition_on_previous_text=False,
            # Primes Whisper to keep the unfamiliar wake word at the start of a
            # sentence. Measured 2026-10-29 on base.en: a bare "Askr." prompt
            # dropped the wake word on 2 of 4 test sentences, this one on 0 of 4.
            # Same trick for any chosen wake word ("Hey Claude": 18/21 -> 21/21).
            initial_prompt=self._prompt,
        )
        return " ".join(s.text.strip() for s in segments).strip()
