"""
Wake-word gate. Always-on listening only acts on speech addressed to askr:
either it starts with the wake word, or it lands inside the follow-up window
that opens whenever askr speaks or accepts an utterance — so a back-and-forth
doesn't need "askr" on every line, but a YouTube video in the background
doesn't drive the session.
"""

import re

FOLLOW_UP_SECS = 20.0

# Whisper has never seen "askr"; these are what it actually hears.
_WAKE_RE = re.compile(
    r"^\W*(?:(?:hey|ok|okay)\W+)?(?:askr|asker|ask\W+her|ask\W+er|ascar|oscar|aska|asca)\b\W*"
    # "Hey askr" run together — heard as "He askedr" / "He asked her" / "He askr".
    r"|^\W*he\W+(?:asked(?:r|\W+her)|askr)\b\W*",
    re.IGNORECASE,
)

# Whisper's stock hallucinations on silence/noise — never a real command.
_NOISE = {
    "", "you", "thank you", "thanks for watching", "thank you for watching",
    "bye", "okay", "ok", "so", "uh", "um", "hmm", "the end",
}


def _is_noise(text: str) -> bool:
    return re.sub(r"[^\w\s]", "", text).strip().lower() in _NOISE


class WakeGate:
    def __init__(self, follow_up_secs: float = FOLLOW_UP_SECS):
        self.follow_up_secs = follow_up_secs
        self._open_until = 0.0

    def open_window(self, now: float):
        """Call when askr finishes speaking — the user's reply needs no wake word."""
        self._open_until = max(self._open_until, now + self.follow_up_secs)

    def accept(self, text: str, now: float) -> str | None:
        """The command to act on (wake word stripped), or None to ignore."""
        text = (text or "").strip()
        match = _WAKE_RE.match(text)
        if match:
            command = text[match.end():].strip()
        elif now < self._open_until:
            command = text
        else:
            return None
        if _is_noise(command):
            # Bare "askr" still opens the window so the next line is heard.
            if match:
                self.open_window(now)
            return None
        self.open_window(now)
        return command
