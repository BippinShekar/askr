"""
`askr voice calibrate` (also runs automatically on first launch).

The user says "askr" a few times. Records (1) how Whisper spells it for this
voice — added to the wake gate's variants — and (2) how loud their speech is
at the mic, which sets the speech-detection floor. Uses a permissive
segmenter so a quiet voice is still captured here even if the default floor
would have missed it entirely.
"""

import queue
import time

import numpy as np

from askr.voice.listener import FRAME_SAMPLES, MicListener, Segmenter
from askr.voice.wake import (_FILLERS, _NOISE, _TOKEN_RE, WakeGate, _edit_distance, _norm,
                             load_profile, save_profile)

ROUNDS = 5
MIN_SAMPLES = 3
_WAIT_SECS = 8.0
_COMMON = _FILLERS | _NOISE | {
    "you", "the", "is", "it", "its", "and", "yes", "yeah", "no", "oh", "what", "ask",
    "as", "us", "if", "thank", "thanks", "okay", "hello", "sir", "her", "are", "is",
    "after", "asked", "asks", "also", "other", "others", "answer",
}


def speech_rms(audio: np.ndarray) -> float:
    """Loudness of the voiced part: 90th-percentile frame RMS. A lone "askr"
    is ~400ms inside ~1.4s of pre-roll and trailing silence, so anything
    wider than the top decile measures the silence."""
    n = len(audio) // FRAME_SAMPLES
    if n == 0:
        return 0.0
    frames = audio[: n * FRAME_SAMPLES].reshape(n, FRAME_SAMPLES)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    return float(np.percentile(rms, 90))


def floor_for(speech_levels: list) -> float:
    """Speech-detection floor: a quarter of the user's quietest attempt, within sane bounds."""
    if not speech_levels:
        return 0.004
    return float(min(0.01, max(0.0015, min(speech_levels) * 0.25)))


def heard_variant(text: str) -> list:
    """Spellings to learn from one attempt: first word, and first two words joined."""
    words = [_norm(t.group()) for t in _TOKEN_RE.finditer(text)]
    words = [w for w in words if w]
    if not words:
        return []
    out = [words[0]]
    if len(words) >= 2:
        out.append(words[0] + words[1])
    return out


def learnable(spelling: str) -> bool:
    """
    Whether a spelling Whisper produced may become a wake variant. Found
    2026-10-30: calibration that picked up a background video learned "you"
    — after which every "you …" in a video would wake it. A learned spelling
    must sound like askr (edit distance from "asker" at most half its length)
    and must not be an everyday word.
    """
    if len(spelling) < 3 or spelling in _COMMON:
        return False
    return _edit_distance(spelling, "asker") <= max(2, (len(spelling) + 1) // 2)


def run(transcriber, display, rounds: int = ROUNDS) -> dict:
    """Collect `rounds` clean samples (up to twice as many attempts). Only a
    calibration with at least MIN_SAMPLES clean samples is saved as done —
    otherwise the next launch asks again instead of trusting bad data."""
    seg = Segmenter(min_rms=0.001, start_ratio=2.0)
    listener = MicListener(segmenter=seg)
    listener.start()
    variants, levels, peak = set(), [], 0.0
    gate = WakeGate()
    display.line("info", f'Calibration: say "askr" on its own, {rounds} times, at your normal volume.')
    try:
        for attempt in range(rounds * 2):
            if len(levels) >= rounds:
                break
            i = len(levels) + 1
            display.line("info", f'  {i}/{rounds} — say "askr" now')
            deadline = time.time() + _WAIT_SECS
            audio = None
            while time.time() < deadline and audio is None:
                try:
                    audio = listener.utterances.get(timeout=0.1)
                except queue.Empty:
                    peak = max(peak, seg.level)
                    display.status(f"waiting {i}/{rounds}", seg.level, seg._threshold())
            if audio is None:
                display.line("error", f"    heard nothing (mic peaked at {peak:.4f})")
                continue
            text = transcriber.transcribe(audio)
            if len(_TOKEN_RE.findall(text)) > 3:
                # A sentence, not "askr" on its own — likely a video or someone else.
                display.line("ignored", f"    heard {text!r} — that's a sentence, not just \"askr\"; again")
                continue
            if not text:
                display.line("ignored", "    heard a sound but no word; again")
                continue
            known = gate.match(text) is not None
            new = [v for v in heard_variant(text) if v not in gate.variants and learnable(v)]
            if not known and not new:
                # Not askr-like: someone/something else. Its loudness mustn't set the floor either.
                display.line("ignored", f"    heard {text!r} — doesn't sound like \"askr\"; again")
                continue
            level = speech_rms(audio)
            levels.append(level)
            if not known:
                variants.add(new[0])
            note = "recognised" if known else f"learned '{new[0]}'"
            display.line("you", f"    heard {text!r}  (level {level:.4f}) — {note}")
    finally:
        listener.stop()

    profile = load_profile()
    if len(levels) < MIN_SAMPLES:
        display.line("error", f"Calibration got {len(levels)} clean samples (need {MIN_SAMPLES}) — not saved. "
                              "If it heard nothing, check the mic permission for Terminal "
                              "(System Settings → Privacy & Security → Microphone).")
        return profile
    profile["variants"] = sorted(set(profile.get("variants", [])) | variants)
    profile["min_rms"] = floor_for(levels)
    profile["speech_rms"] = float(np.median(levels))
    profile["calibrated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_profile(profile)
    display.line("info", f"Saved: speech floor {profile['min_rms']:.4f}, "
                         f"learned spellings: {', '.join(profile['variants']) or 'none needed'}")
    return profile
