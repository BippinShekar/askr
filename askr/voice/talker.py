"""
The conversational half. Claude Code does the work; the talker is a fast
model that holds the spoken back-and-forth: it answers from the session
digest, asks a clarifying question when the request is ambiguous, and
decides what (if anything) to hand to Claude Code — cleaned of speech-to-text
errors and phrased as an instruction.
"""

import json
import re
from dataclasses import dataclass

# Same model as askr's other OAuth calls. claude-haiku-5-5 and claude-sonnet-5-5
# both return HTTP 429 over Claude Code's OAuth token (checked 2026-10-29 at 10%
# quota) while this one answers — revisit when that changes.
VOICE_MODEL = "claude-haiku-4-5-20251001"
_MAX_HISTORY = 12  # messages (user+assistant) of spoken conversation kept

SYSTEM = """You are askr's voice: the spoken companion to a Claude Code session the user is running.
Claude Code is the worker that edits code and runs commands. You never do the work yourself.
You talk with the user out loud, and decide what to pass to Claude Code.

Each turn you get the user's words (from local speech-to-text, so expect mishearings —
e.g. "link" for "lint", "get" for "git"; fix them using context) and a digest of what
the Claude Code session is doing.

Reply with ONLY a JSON object:
{"say": "...", "send": "..." or null}

- "say": what to speak back. One or two short sentences, plain spoken English: no markdown,
  no code, no file paths read character by character. Confirm what you're passing on,
  answer status questions from the digest, or ask ONE clarifying question if the request is
  genuinely ambiguous. Don't invent progress that isn't in the digest.
- "send": the message for Claude Code, or null. Write it as a clear instruction or piece of
  context in the user's voice, keeping every concrete detail they gave (names, numbers,
  constraints). If a turn is running, it reaches Claude Code mid-task as extra context, so
  phrase it so it can be applied to the current work ("Also skip the flaky auth test").
  If no turn is running, it becomes the next prompt.
- Questions about status/progress, small talk, and clarifying exchanges: send null.
- When the user answers your clarifying question, send the combined, complete request.
- "stop", "cancel", "never mind" about the current task: send "Stop what you're doing and wait for further instructions." and say you've asked it to stop."""


@dataclass
class Reply:
    say: str
    send: str | None = None


def _parse(text: str) -> Reply:
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        data = {}
    say = str(data.get("say") or "").strip()
    send = data.get("send")
    send = str(send).strip() if send else None
    if not say and not send:
        return Reply(say="Sorry, I didn't get that.")
    return Reply(say=say or "Passing that on.", send=send or None)


class Talker:
    def __init__(self, post=None):
        # Injected for tests; defaults to askr's OAuth transport (Claude Code login).
        if post is None:
            from askr.clients.claude import _post_messages as post
        self._post = post
        self.history: list = []

    def respond(self, utterance: str, session_digest: str) -> Reply:
        user = f"Session digest:\n{session_digest}\n\nUser said: {utterance}"
        messages = self.history + [{"role": "user", "content": user}]
        try:
            data = self._post({
                "model": VOICE_MODEL,
                "max_tokens": 400,
                "system": SYSTEM,
                "messages": messages,
            }, "voice", utterance[:80])
            text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        except Exception as e:
            from askr.utils.logger import log_error
            log_error("voice.talker", str(e))
            return Reply(say="I couldn't reach Claude just now.")
        reply = _parse(text)
        # History keeps only what was said, not the digests — they go stale and
        # would crowd the window; the current digest arrives with every turn.
        self.history = (self.history + [
            {"role": "user", "content": utterance},
            {"role": "assistant", "content": json.dumps({"say": reply.say, "send": reply.send})},
        ])[-_MAX_HISTORY:]
        return reply

    def narrate(self, update: str, request: str) -> str:
        """Turn Claude Code's written output into a short spoken update (stage 4)."""
        try:
            data = self._post({
                "model": VOICE_MODEL,
                "max_tokens": 200,
                "system": ("Rewrite a coding agent's message as one or two short spoken sentences for "
                           "the user who asked it something by voice. Plain English, no markdown, no "
                           "paths or code read out, no filler. Keep concrete outcomes: what changed, "
                           "what passed or failed, and any question it's asking the user. "
                           "Reply with only the sentences."),
                "messages": [{"role": "user", "content": f"User's request: {request}\n\nAgent's message:\n{update}"}],
            }, "voice_narrate", update[:80])
            return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        except Exception as e:
            from askr.utils.logger import log_error
            log_error("voice.narrate", str(e))
            return ""
