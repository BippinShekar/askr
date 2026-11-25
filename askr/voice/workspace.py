"""
Where the user is, for the voice agent — and opening terminals there.

The IDE extension writes voice_focus.json whenever a window gains focus or
its terminals change: the window's name and folders, its terminals, the
active one. Found 2026-11-25: without this the agent asked "which window?"
when told to "open the untitled workspace terminal" — it knew nothing
about the editor it was running in.
"""

import json
import os
import shlex
import time
import uuid

from askr.voice import daemon

OPEN_TERMINAL_PATH = os.path.join(os.path.dirname(daemon.FOCUS_PATH), "voice_open_terminal.json")
_CLAIM_TIMEOUT_SECS = 6.0


def read_focus() -> dict:
    try:
        with open(daemon.FOCUS_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _home(path: str) -> str:
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home) else path


def describe(focus: dict, session_cwd: str = "") -> str:
    """A few lines of orientation for the agent; '' if nothing is known."""
    lines = []
    if focus:
        window = focus.get("workspace") or "untitled"
        folders = ", ".join(_home(f) for f in focus.get("folders") or []) or "no folder"
        lines.append(f"The user is in Cursor, window \"{window}\" ({folders}) — \"this window\"/\"here\" means it.")
        terms = focus.get("terminals") or []
        if terms:
            active = focus.get("name") or ""
            lines.append("Its terminals: " + ", ".join(terms) + (f" (active: {active})" if active else "") + ".")
    if session_cwd:
        lines.append(f"The Claude Code session you send instructions to runs in {_home(session_cwd)}.")
    return " ".join(lines)


def open_terminal(cwd: str = "", command: str = "", name: str = "askr", clock=time.time) -> str:
    """Ask the window the user was last in to open a terminal (and run `command`)."""
    focus = read_focus()
    req = {"id": uuid.uuid4().hex, "cwd": cwd, "command": command, "name": name,
           "ext_pid": focus.get("ext_pid") or 0, "ts": clock()}
    os.makedirs(os.path.dirname(OPEN_TERMINAL_PATH), exist_ok=True)
    tmp = f"{OPEN_TERMINAL_PATH}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(req, f)
    os.replace(tmp, OPEN_TERMINAL_PATH)
    deadline = clock() + _CLAIM_TIMEOUT_SECS
    while clock() < deadline:
        if not os.path.exists(OPEN_TERMINAL_PATH):
            return f"opened a terminal{' in ' + _home(cwd) if cwd else ''}" + (" running " + command if command else "")
        time.sleep(0.2)
    try:
        os.remove(OPEN_TERMINAL_PATH)
    except OSError:
        pass
    return "error: the editor didn't open it — is the askr extension running in Cursor?"


def claude_command(prompt: str = "") -> str:
    return "claude" + (" " + shlex.quote(prompt) if prompt else "")
