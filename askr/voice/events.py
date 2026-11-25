"""
"Claude needs you" events from the Notification hook to the voice daemon.

Claude Code fires Notification when it's blocked on the user: a permission
prompt, a question dialog, or sitting idle waiting for input. The hook drops
one file per event here; the voice loop says it out loud in one short line
(askr/voice/loop.py speak_events). Files, not a socket, so a hook never
blocks on the daemon and nothing is lost if the daemon is restarting.
"""

import json
import os
import time
import uuid

EVENTS_DIR = os.path.expanduser("~/.config/askr/voice_events")
_MAX_AGE_SECS = 120  # older than this when read: stale, dropped unspoken

# Notification types worth saying out loud (Claude Code's notification_type).
SPOKEN_TYPES = {"permission_prompt", "elicitation_dialog", "idle_prompt"}
# "announce": any other askr process's line, handed over so only the daemon speaks.


def post(session_id: str, kind: str, message: str, cwd: str = ""):
    os.makedirs(EVENTS_DIR, exist_ok=True)
    path = os.path.join(EVENTS_DIR, f"{time.time():.3f}-{uuid.uuid4().hex[:6]}.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"session_id": session_id, "kind": kind, "message": message, "cwd": cwd,
                   "ts": time.time()}, f)
    os.replace(tmp, path)


def drain(now: float | None = None) -> list:
    """Take every pending event (oldest first), dropping stale ones."""
    now = time.time() if now is None else now
    try:
        names = sorted(n for n in os.listdir(EVENTS_DIR) if n.endswith(".json"))
    except OSError:
        return []
    out = []
    for name in names:
        path = os.path.join(EVENTS_DIR, name)
        try:
            with open(path) as f:
                event = json.load(f)
            os.remove(path)
        except (OSError, ValueError):
            continue
        if now - float(event.get("ts") or 0) <= _MAX_AGE_SECS:
            out.append(event)
    return out


def spoken(event: dict, same_session: bool) -> str:
    """One short line for an event, in askr's voice style."""
    kind, msg = event.get("kind"), (event.get("message") or "").strip()
    where = "" if same_session else f"over in {os.path.basename(event.get('cwd') or '') or 'another session'}, "
    if kind == "announce":
        return msg
    if kind == "permission_prompt":
        what = msg.replace("Claude needs your permission to ", "").rstrip(".")
        line = f"{where}it needs your OK to {what}" if what and what != msg else f"{where}it needs your permission"
    elif kind == "elicitation_dialog":
        line = f"{where}it's asking you something"
    else:
        line = f"{where}it's waiting on you"
    return line[0].upper() + line[1:]
