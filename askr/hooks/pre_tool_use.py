#!/usr/bin/env python3
"""
Claude Code Hook - PreToolUse

Fires before every tool execution. Tracks write operations per session and
writes guard_trigger.json when a significance threshold is crossed, signalling
the guard engine (Stage 2) to run a Haiku architecture cross-check.

Significance thresholds:
  - First new file creation (Write to a path that doesn't exist yet)
  - 3rd file edit in a session (batch implementation detected)
  - Edit to a file listed as a core/shared interface in architecture.md

Non-blocking: always exits 0 so Claude's tool is never prevented here.
The guard engine runs asynchronously in Stage 3.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_GUARD_SESSION_PATH  = os.path.expanduser("~/.config/askr/guard_session.json")
_GUARD_TRIGGER_PATH  = os.path.expanduser("~/.config/askr/guard_trigger.json")
_GUARD_COOLDOWN_SECS = 300  # don't re-trigger within 5 minutes
_BATCH_THRESHOLD     = 3    # N file edits before a batch trigger fires


def _load_session() -> dict:
    try:
        if os.path.exists(_GUARD_SESSION_PATH):
            with open(_GUARD_SESSION_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {"write_count": 0, "last_trigger_at": None, "session_date": _today()}


def _save_session(data: dict):
    try:
        os.makedirs(os.path.dirname(_GUARD_SESSION_PATH), exist_ok=True)
        with open(_GUARD_SESSION_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _in_cooldown(session: dict) -> bool:
    last = session.get("last_trigger_at")
    if not last:
        return False
    try:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        return elapsed < _GUARD_COOLDOWN_SECS
    except Exception:
        return False


def _is_new_file(path: str) -> bool:
    if not path:
        return False
    return not os.path.exists(path)


def _is_shared_interface(path: str) -> bool:
    """Check if the file is flagged as a core/shared interface in architecture.md."""
    if not path:
        return False
    try:
        from askr.state.config import state_path
        arch_path = state_path("architecture.md")
        if not os.path.exists(arch_path):
            return False
        with open(arch_path) as f:
            content = f.read()
        filename = os.path.basename(path)
        # Flag if the filename appears in architecture.md in a "core" or "shared" context
        lower = content.lower()
        name_lower = filename.lower()
        idx = lower.find(name_lower)
        if idx == -1:
            return False
        surrounding = lower[max(0, idx - 80):idx + 80]
        return any(k in surrounding for k in ("core", "shared", "interface", "api", "entry"))
    except Exception:
        return False


def _write_trigger(reason: str, tool_name: str, file_path: str):
    try:
        os.makedirs(os.path.dirname(_GUARD_TRIGGER_PATH), exist_ok=True)
        with open(_GUARD_TRIGGER_PATH, "w") as f:
            json.dump({
                "reason": reason,
                "tool": tool_name,
                "file_path": file_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    # Only care about write/edit operations
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    try:
        from askr.state.config import get_state_dir
        if not os.path.isdir(get_state_dir()):
            sys.exit(0)
    except Exception:
        sys.exit(0)

    file_path = tool_input.get("file_path") or tool_input.get("path", "")

    # Skip askr's own state files — guard is for project code, not state artifacts
    if "askr_state" in file_path or ".claude" in file_path:
        sys.exit(0)

    session = _load_session()

    # Reset counter if it's a new day
    if session.get("session_date") != _today():
        session = {"write_count": 0, "last_trigger_at": None, "session_date": _today()}

    if _in_cooldown(session):
        sys.exit(0)

    session["write_count"] = session.get("write_count", 0) + 1

    trigger_reason = None

    if tool_name == "Write" and _is_new_file(file_path):
        trigger_reason = "new_file"
    elif session["write_count"] == _BATCH_THRESHOLD:
        trigger_reason = "batch_writes"
    elif _is_shared_interface(file_path):
        trigger_reason = "shared_interface"

    if trigger_reason:
        session["last_trigger_at"] = datetime.now(timezone.utc).isoformat()
        _write_trigger(trigger_reason, tool_name, file_path)

    _save_session(session)
    sys.exit(0)


if __name__ == "__main__":
    main()
