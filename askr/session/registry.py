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


def is_session_confirmed_dead(session_id: str) -> bool:
    """
    True ONLY when there is positive proof this session's process has
    exited — a registered PID that no longer responds to signal 0. False
    for everything else, including "no registry entry at all." Unknown is
    not dead.

    This function exists specifically for pruning lifecycle.py's
    companioned_sessions dedup, and its asymmetry is deliberate: the cost
    of never pruning a session we can't confirm dead (a stale id sitting
    harmlessly in a small JSON set forever) is trivial next to the cost of
    wrongly pruning one that's still alive (a companion re-fires on a
    session the user never touched, closed, or finished with).

    History of getting this wrong, both 2026-07-11:
    - First pass pruned against stats freshness (SESSION_STALE_SECS, 10
      min). Stats go stale whenever the Mac sleeps or a window sits idle,
      not just when a session ends — waking the machine after any longer
      nap re-triggered a companion for a session that was never closed.
    - Second pass (this function's predecessor, is_session_pid_alive)
      fixed that by checking the registry's recorded PID instead — but
      treated "no registry entry" the same as "confirmed dead." Session
      registration (register_session(), called from SessionStart) is
      wrapped in a bare except Exception: pass and silently no-ops for
      sessions that started before it existed, or during any gap where the
      hook didn't fire as expected. Confirmed directly: of the dozens of
      distinct sessions active today, exactly one had a registry entry —
      including this very multi-hour conversation, unambiguously alive,
      which had none. Every unregistered session was being pruned on the
      very next poll cycle after being companioned, regardless of
      liveness, sleep, or anything else.
    """
    if not session_id:
        return False
    try:
        with open(_session_file(session_id)) as f:
            entry = json.load(f)
    except Exception:
        return False  # no entry — unknown, not confirmed dead
    pid = entry.get("pid")
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return False  # alive
    except OSError:
        return True  # confirmed dead


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
