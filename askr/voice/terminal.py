"""
Starting a new turn in an idle session by typing into its terminal.

Mid-turn input goes through the hook inbox (inbox.py); but a session that's
waiting for the user has no hook running, so a new request has to be typed
into its terminal. The askr IDE extension does the typing, matching the
terminal by the claude process's ancestor PIDs.

That PID is recorded by the session's own hooks (SessionStart and
UserPromptSubmit) — the hook process is a descendant of exactly one claude,
so this never has to guess between several sessions in the same repo (the
cwd-based guess is what killed the wrong session on 2026-10-27).
"""

import json
import os
import subprocess
import time
import uuid

_PIDS_DIR = os.path.expanduser("~/.config/askr/session_pids")
_VOICE_PROMPT_PATH = os.path.expanduser("~/.config/askr/voice_prompt.json")


def _own_claude_pid(max_depth: int = 8) -> int | None:
    current = os.getppid()
    for _ in range(max_depth):
        if current <= 1:
            return None
        try:
            out = subprocess.run(["ps", "-o", "ppid=,comm=", "-p", str(current)],
                                 capture_output=True, text=True, timeout=3).stdout.strip()
        except Exception:
            return None
        ppid, _, comm = out.partition(" ")
        if not ppid:
            return None
        if os.path.basename(comm.strip()) == "claude":
            return current
        try:
            current = int(ppid)
        except ValueError:
            return None
    return None


def record_own_pid(session_id: str):
    """Called from hooks: remember which claude process owns this session."""
    if not session_id:
        return
    pid = _own_claude_pid()
    if not pid:
        return
    try:
        os.makedirs(_PIDS_DIR, exist_ok=True)
        with open(os.path.join(_PIDS_DIR, session_id), "w") as f:
            f.write(str(pid))
    except OSError:
        pass


def session_pid(session_id: str) -> int | None:
    try:
        with open(os.path.join(_PIDS_DIR, session_id)) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def type_prompt(session_id: str, text: str, project_path: str = "") -> bool:
    """Ask the IDE extension to type `text` + Enter into this session's terminal."""
    pid = session_pid(session_id)
    if not pid:
        return False
    from askr.session.lifecycle import _get_ancestor_pids
    payload = {
        "id": uuid.uuid4().hex,
        "text": text,
        "ancestor_pids": [pid] + _get_ancestor_pids(pid),
        "project_path": project_path,
        "shown": False,
        "timestamp": time.time(),
    }
    os.makedirs(os.path.dirname(_VOICE_PROMPT_PATH), exist_ok=True)
    tmp = f"{_VOICE_PROMPT_PATH}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(payload, f)
    os.replace(tmp, _VOICE_PROMPT_PATH)
    return True
