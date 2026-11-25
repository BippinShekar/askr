"""
Always-on listening: decide whether a line was said *to* askr.

With no wake word, everything the mic hears is a candidate — the user
talking to askr, but also videos, music and the user talking to someone
else. Cheap local filters drop what obviously isn't a request (long
monologue chunks, Whisper's noise hallucinations); what's left gets one
tiny Haiku yes/no call. A rate cap keeps a talkative video from burning
the subscription's quota.

The wake word still works as an instant override (no call), and inside an
open conversation every line counts (no call either).
"""

import collections
import re
import time

from askr.voice.talker import VOICE_MODEL
from askr.voice.wake import _is_noise

MAX_WORDS = 40          # longer than any spoken request; typical of a video/podcast chunk
MIN_WORDS = 1  # "stop", "cancel" — Whisper noise ("you", "okay") is filtered separately
MAX_CHECKS_PER_MIN = 15

SYSTEM = """You're the listening filter for askr, a voice assistant on a developer's laptop. The mic hears everything: the developer talking to askr, but also videos, music, podcasts, calls, and the developer talking to other people.

Decide if this one line was said TO the assistant: a request, instruction or question for it or for their coding agent ("run the tests", "what's it doing", "open YouTube", "tell it to push", "approve that", "look up X"), or a reply in an exchange the assistant just had with them.
Not for it: anything that sounds like a video, podcast, song, narration or ad; one side of a phone call or a chat with someone in the room; thinking out loud with no ask.
When unsure, it's not for it.

Reply with only: yes or no"""


class Addressee:
    def __init__(self, post=None, clock=time.time):
        if post is None:
            from askr.clients.claude import _post_messages as post
        self._post = post
        self.clock = clock
        self._checks = collections.deque()

    def worth_checking(self, text: str) -> str:
        """'' if the line should go to the model; otherwise why it was skipped."""
        words = re.findall(r"[A-Za-z0-9']+", text or "")
        if _is_noise(text) or len(words) < MIN_WORDS:
            return "too short / noise"
        if len(words) > MAX_WORDS:
            return "too long to be a request"
        now = self.clock()
        while self._checks and now - self._checks[0] > 60:
            self._checks.popleft()
        if len(self._checks) >= MAX_CHECKS_PER_MIN:
            return "too much talking — rate-capped"
        return ""

    def is_for_askr(self, text: str, last_said: str = "") -> bool:
        self._checks.append(self.clock())
        context = f'The assistant last said: "{last_said}"\n' if last_said else ""
        try:
            data = self._post({"model": VOICE_MODEL, "max_tokens": 3, "system": SYSTEM,
                               "messages": [{"role": "user", "content": f'{context}Line heard: "{text}"'}]},
                              "voice_addressee", text[:80])
        except Exception:
            return False
        answer = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return answer.strip().lower().startswith("yes")
