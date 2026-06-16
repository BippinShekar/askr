"""
Session registry — tracks active Claude Code sessions per project.

Each session writes its own file under askr_state/sessions/{session_id}.json.
No shared-file writes, so no locking needed. Stale sessions are detected by
PID liveness check (os.kill(pid, 0)) and heartbeat age.
"""

import os
import json
import glob
from datetime import datetime, timezone, timedelta

_HEARTBEAT_STALE_MINUTES = 5


def _sessions_dir() -> str:
    from askr.state.config import get_state_dir
    return os.path.join(get_state_dir(), "sessions")


def _session_file(session_id: str) -> str:
    return os.path.join(_sessions_dir(), f"{session_id}.json")


def register_session(session_id: str, developer: str, pid=None):
    """Write this session's registry entry. Called at session start."""
    if not session_id:
        return
    pid = pid or os.getpid()
    os.makedirs(_sessions_dir(), exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    entry = {
        "session_id": session_id,
        "dev": developer,
        "pid": pid,
        "started_at": now,
        "last_heartbeat": now,
    }
    with open(_session_file(session_id), "w") as f:
        json.dump(entry, f, indent=2)


def update_heartbeat(session_id: str):
    """Update last_heartbeat timestamp. Called periodically from post_tool_use."""
    if not session_id:
        return
    path = _session_file(session_id)
    if not os.path.exists(path):
        return
    try:
        with open(path) as f:
            entry = json.load(f)
        entry["last_heartbeat"] = datetime.now(timezone.utc).isoformat()
        with open(path, "w") as f:
            json.dump(entry, f, indent=2)
    except Exception:
        pass


def deregister_session(session_id: str):
    """Remove this session's registry entry. Called at session stop."""
    if not session_id:
        return
    path = _session_file(session_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except Exception:
        pass


def _is_alive(entry: dict) -> bool:
    """True if the session's PID is still running and heartbeat is fresh."""
    pid = entry.get("pid")
    if pid:
        try:
            os.kill(pid, 0)
        except OSError:
            return False

    hb = entry.get("last_heartbeat", "")
    if hb:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(hb)
            if age > timedelta(minutes=_HEARTBEAT_STALE_MINUTES):
                return False
        except Exception:
            pass
    return True


def get_active_sessions(exclude_session_id: str = "") -> list[dict]:
    """Return entries for all live sibling sessions (excluding our own)."""
    sessions_dir = _sessions_dir()
    if not os.path.isdir(sessions_dir):
        return []

    active = []
    for path in glob.glob(os.path.join(sessions_dir, "*.json")):
        try:
            with open(path) as f:
                entry = json.load(f)
        except Exception:
            continue

        sid = entry.get("session_id", "")
        if sid == exclude_session_id:
            continue

        if _is_alive(entry):
            active.append(entry)
        else:
            # Clean up stale entry
            try:
                os.remove(path)
            except Exception:
                pass

    return active
