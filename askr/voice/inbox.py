"""
Fallback for spoken input when the session's terminal can't be typed into
(terminal.type_prompt is the primary route). The Stop hook drains it and
makes Claude keep going with it at the end of the running turn.

Not delivered mid-turn via PostToolUse additionalContext: tested live
2026-10-29 — Claude receives it inside the tool result, treats an
instruction there as prompt injection, and (correctly) refuses it. The Stop
hook's block reason is acted on.
"""

import json
import os
import time

_INBOX_DIR = os.path.expanduser("~/.config/askr/voice_inbox")


def _path(session_id: str) -> str:
    return os.path.join(_INBOX_DIR, f"{session_id}.jsonl")


def post(session_id: str, text: str):
    os.makedirs(_INBOX_DIR, exist_ok=True)
    with open(_path(session_id), "a") as f:
        f.write(json.dumps({"text": text, "at": time.time()}) + "\n")


def pending(session_id: str) -> bool:
    return bool(session_id) and os.path.exists(_path(session_id))


def drain(session_id: str) -> list:
    """Atomically claim and return every queued message (oldest first)."""
    if not session_id:
        return []
    src = _path(session_id)
    claimed = f"{src}.{os.getpid()}.claimed"
    try:
        os.rename(src, claimed)  # atomic: a concurrent post() starts a fresh file
    except OSError:
        return []
    messages = []
    try:
        with open(claimed) as f:
            for line in f:
                try:
                    text = json.loads(line).get("text", "").strip()
                except Exception:
                    continue
                if text:
                    messages.append(text)
    finally:
        try:
            os.remove(claimed)
        except OSError:
            pass
    return messages


def as_context(messages: list) -> str:
    joined = "\n".join(f"- {m}" for m in messages)
    return ("The user just said this by voice while you were working (relayed by askr). "
            "Apply it to the current task:\n" + joined)
