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
DEFAULT_WORD = "askr"
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
# Spellings that are real words — they only wake it at the start of an
# utterance or right after a sentence break, never mid-sentence.
_WEAK = {"oscar", "aska", "asca", "masker", "tasker", "basker"}

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


def phrase_key(phrase: str) -> str:
    """"Heads up" -> "headsup": how a wake phrase is compared, tokens joined."""
    return "".join(_norm(t) for t in _TOKEN_RE.findall(phrase or ""))


class WakeGate:
    """`word` is the wake word or phrase (profile "wake_word"); "askr" — the
    default — also gets the built-in Whisper spellings and fuzzy matching tuned
    for it. Any other word matches exactly (tokens joined) or one edit away."""

    def __init__(self, follow_up_secs: float = FOLLOW_UP_SECS, variants=(), word: str = DEFAULT_WORD):
        self.follow_up_secs = follow_up_secs
        self.word = word or DEFAULT_WORD
        self.is_askr = phrase_key(self.word) == "askr"
        self.targets = _TARGETS if self.is_askr else (phrase_key(self.word),)
        self._span = 2 if self.is_askr else max(1, len(_TOKEN_RE.findall(self.word))) + 1
        builtin = _BUILTIN if self.is_askr else {phrase_key(self.word)}
        self.variants = builtin | {_norm(v) for v in variants if _norm(v)}
        self._open_until = 0.0

    def _is_wake(self, word: str) -> bool:
        if word in self.variants:
            return True
        if word in _NOT_WAKE or len(word) < (4 if self.is_askr else 5):
            return False
        return any(_edit_distance(word, t) <= 1 for t in self.targets)

    def _match_at(self, tokens, start: int) -> int | None:
        # Longest span first: "ask her" (askr) or "heads up" arrive as several tokens.
        for k in range(min(self._span, len(tokens) - start), 1, -1):
            joined = "".join(_norm(t.group()) for t in tokens[start:start + k])
            if joined in self.variants or (not self.is_askr and self._is_wake(joined)):
                return tokens[start + k - 1].end()
        if self._is_wake(_norm(tokens[start].group())):
            return tokens[start].end()
        return None

    def match(self, text: str) -> int | None:
        """Character offset just past the wake word, or None if there isn't one."""
        tokens = list(_TOKEN_RE.finditer(text))
        i = 0
        while i < len(tokens) and i < 2 and _norm(tokens[i].group()) in _FILLERS:
            i += 1
        for start in sorted({0, i}):
            if start < len(tokens):
                end = self._match_at(tokens, start)
                if end is not None:
                    return end
        # Mid-utterance. With a video or music playing the segmenter never
        # hears silence, so "askr, run the tests" arrives glued onto whatever
        # was playing — the wake word is no longer first. Mid-text only counts
        # after a sentence break, or as a spelling that isn't ordinary English
        # ("…to ask her later" must not wake it).
        for start in range(1, len(tokens)):
            before = text[tokens[start - 1].end():tokens[start].start()]
            end = self._match_at(tokens, start)
            if end is None:
                continue
            if re.search(r"[.?!]", before) or self._is_strong(text[tokens[start].start():end]):
                return end
        return None

    def _is_strong(self, spoken: str) -> bool:
        # Only askr's invented spellings are safe mid-sentence; a chosen real
        # word ("terminal") mid-sentence is just someone using the word.
        word = _norm(spoken)
        return self.is_askr and " " not in spoken.strip() and word not in _WEAK and len(word) >= 4

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
