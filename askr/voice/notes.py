"""
Dictation into Apple Notes: "askr, transcribe what I say into Notes".

While on, every utterance — no wake word needed — is appended to one note,
one paragraph per utterance, as soon as it's transcribed. "Stop taking
notes" (or "stop dictation") ends it. State lives in voice_notes.json so
`askr voice notes on|off` and the voice command agree.
"""

import html
import json
import os
import re
import subprocess
import time

STATE_PATH = os.path.expanduser("~/.config/askr/voice_notes.json")

_START_RE = re.compile(r"\b(notes? app|into notes|in notes|onto notes|to notes|take notes|"
                       r"taking notes|start dictat\w*)\b", re.I)
_START_VERB_RE = re.compile(r"\b(transcrib\w*|dictat\w*|write|type|take|put|jot|note)\b", re.I)
_STOP_RE = re.compile(r"\b(stop|end|quit|finish|done)\b.{0,20}\b(notes?|dictat\w*|transcrib\w*)\b", re.I)


def wants_start(command: str) -> bool:
    return bool(_START_RE.search(command) and _START_VERB_RE.search(command)) and not wants_stop(command)


def wants_stop(text: str) -> bool:
    return bool(_STOP_RE.search(text))


def active() -> dict | None:
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def start(now: float | None = None) -> str:
    title = time.strftime("askr dictation — %Y-%m-%d %H:%M", time.localtime(now))
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w") as f:
        json.dump({"title": title, "started": now or time.time()}, f)
    _osascript(_script(title, "", create_only=True))
    return title


def stop():
    try:
        os.remove(STATE_PATH)
    except OSError:
        pass


def append(text: str) -> bool:
    state = active()
    if not state or not text.strip():
        return False
    return _osascript(_script(state["title"], f"<div>{html.escape(text.strip())}</div>"))


def _as_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _script(title: str, body_html: str, create_only: bool = False) -> str:
    t, b = _as_string(title), _as_string(body_html)
    append_line = "" if create_only else f"\n    set body of n to (body of n) & {b}"
    return f'''tell application "Notes"
  set found to (notes whose name is {t})
  if (count of found) is 0 then
    set n to make new note with properties {{body:"<h1>" & {_as_string(html.escape(title))} & "</h1>"}}
  else
    set n to item 1 of found
  end if{append_line}
end tell'''


def _osascript(script: str) -> bool:
    try:
        return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=15).returncode == 0
    except Exception:
        return False
