#!/usr/bin/env python3
"""
Claude Code Hook - PreToolUse

Fires before every tool execution. On significant write operations runs a
synchronous guard check. If architectural issues are found, blocks the write
and surfaces the reason directly to Claude so it can self-correct.

Significance thresholds:
  - First new file creation (Write to a path that doesn't exist yet)
  - 3rd file edit in a session (batch implementation detected)
  - Edit to a file listed as a core/shared interface in architecture.md

Blocking: outputs {"decision": "block", "reason": "..."} + exits 2 when
guard detects a real architectural contradiction. Exits 0 (allow) otherwise.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_GUARD_SESSION_PATH  = os.path.expanduser("~/.config/askr/guard_session.json")
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
        lower = content.lower()
        name_lower = filename.lower()
        idx = lower.find(name_lower)
        if idx == -1:
            return False
        surrounding = lower[max(0, idx - 80):idx + 80]
        return any(k in surrounding for k in ("core", "shared", "interface", "api", "entry"))
    except Exception:
        return False


def _block_tool(reason: str):
    """Output block decision to stdout and exit 2 to prevent the tool from running."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


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
        trigger = {
            "reason": trigger_reason,
            "tool": tool_name,
            "file_path": file_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = _run_guard(trigger)

        if not result.get("clean", True):
            # Do NOT update last_trigger_at — blocked writes must not enter cooldown
            # so the corrected retry will also be checked.
            _save_session(session)
            _on_block(result, file_path, trigger_reason)
            # _on_block calls _block_tool which exits — nothing below runs on block
        else:
            session["last_trigger_at"] = datetime.now(timezone.utc).isoformat()

    _save_session(session)
    sys.exit(0)


def _run_guard(trigger: dict) -> dict:
    """Run guard check synchronously. Returns {"clean": True} on any failure."""
    try:
        from askr.state.config import load_developer, get_state_dir
        from askr.session.guard import run_guard_check
        developer = load_developer()
        state_dir = get_state_dir()
        return run_guard_check(trigger, developer, state_dir)
    except Exception:
        return {"clean": True}


def _on_block(result: dict, file_path: str, trigger_reason: str):
    """Format and emit the block signal. Does not return (exits 2)."""
    issues  = result.get("issues", [])
    summary = result.get("summary", "Architectural issue detected.")

    issues_text = "\n".join(f"• {i}" for i in issues) if issues else ""
    block_reason = (
        f"Guard blocked: {summary}"
        + (f"\n\n{issues_text}" if issues_text else "")
        + "\n\nRevise your approach to address these architectural concerns before proceeding."
    )

    _block_tool(block_reason)


if __name__ == "__main__":
    main()
