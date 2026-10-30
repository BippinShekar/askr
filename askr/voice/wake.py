"""
Wake-word gate. Always-on listening only acts on speech addressed to askr:
either it starts with the wake word, or it lands inside the follow-up window
that opens whenever askr speaks or accepts an utterance — so a back-and-forth
doesn't need "askr" on every line, but a YouTube video in the background
doesn't drive the session.

"askr" isn't a word Whisper knows, and how it spells it depends on the
speaker's accent. Matching is therefore fuzzy (built-in spellings, plus
anything one edit from "asker"), and `askr voice calibrate` adds the exact
spellings Whisper produces for this user's voice (voice_profile.json).
"""

import json
import os
import re

FOLLOW_UP_SECS = 20.0
PROFILE_PATH = os.path.expanduser("~/.config/askr/voice_profile.json")

# Spellings Whisper produced for "askr" in testing (single tokens, or two
# adjacent tokens joined: "ask her" -> "askher").
_BUILTIN = {"askr", "asker", "askher", "askar", "ascar", "oscar", "aska", "asca",
            "askedr", "askedher", "asgar", "asgr", "askur"}
_TARGETS = ("asker", "askr")
# One edit from a target but ordinary English — "Asked him to…" in a video
# must not wake it. Calibration can still learn one if it's how Whisper
# spells this user's "askr".
_NOT_WAKE = {"asked", "asks", "aster", "ashes", "asset"}
# May precede the wake word ("Hey askr", "Okay, askr", Whisper's "He askedr").
_FILLERS = {"hey", "hi", "ok", "okay", "so", "um", "uh", "he", "yo", "and"}

# Whisper's stock hallucinations on silence/noise — never a real command.
_NOISE = {
    "", "you", "thank you", "thanks for watching", "thank you for watching",
    "bye", "okay", "ok", "so", "uh", "um", "hmm", "the end",
}

_TOKEN_RE = re.compile(r"[A-Za-z']+")


def _norm(token: str) -> str:
    return re.sub(r"[^a-z]", "", token.lower())


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _is_noise(text: str) -> bool:
    return re.sub(r"[^\w\s]", "", text).strip().lower() in _NOISE


def load_profile() -> dict:
    try:
        with open(PROFILE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_profile(profile: dict):
    os.makedirs(os.path.dirname(PROFILE_PATH), exist_ok=True)
    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)


class WakeGate:
    def __init__(self, follow_up_secs: float = FOLLOW_UP_SECS, variants=()):
        self.follow_up_secs = follow_up_secs
        self.variants = _BUILTIN | {_norm(v) for v in variants if _norm(v)}
        self._open_until = 0.0

    def _is_wake(self, word: str) -> bool:
        if word in self.variants:
            return True
        if word in _NOT_WAKE or len(word) < 4:
            return False
        return any(_edit_distance(word, t) <= 1 for t in _TARGETS)

    def match(self, text: str) -> int | None:
        """Character offset just past the wake word, or None if it doesn't start the text."""
        tokens = list(_TOKEN_RE.finditer(text))
        i = 0
        while i < len(tokens) and i < 2 and _norm(tokens[i].group()) in _FILLERS:
            i += 1
        for start in sorted({0, i}):
            if start >= len(tokens):
                continue
            first = _norm(tokens[start].group())
            if start + 1 < len(tokens):
                pair = first + _norm(tokens[start + 1].group())
                if pair in self.variants:
                    return tokens[start + 1].end()
            if self._is_wake(first):
                return tokens[start].end()
        return None

    def open_window(self, now: float):
        """Call when askr finishes speaking — the user's reply needs no wake word."""
        self._open_until = max(self._open_until, now + self.follow_up_secs)

    def accept(self, text: str, now: float) -> str | None:
        """The command to act on (wake word stripped), or None to ignore."""
        text = (text or "").strip()
        end = self.match(text)
        if end is not None:
            command = re.sub(r"^\W+", "", text[end:]).strip()
        elif now < self._open_until:
            command = text
        else:
            return None
        if _is_noise(command):
            # Bare "askr" still opens the window so the next line is heard.
            if end is not None:
                self.open_window(now)
            return None
        self.open_window(now)
        return command
