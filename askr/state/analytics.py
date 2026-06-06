"""
Session time-saved analytics.

Tracks wall-clock duration of each Claude session. "Time saved" = time Claude
was working autonomously so a developer didn't have to.

Storage: ~/.config/askr/analytics.json — append-only list of session entries.
"""

import os
import json
from datetime import datetime, timezone

_ANALYTICS_PATH   = os.path.expanduser("~/.config/askr/analytics.json")
_SESSION_START_PATH = os.path.expanduser("~/.config/askr/session_start.json")


def record_session_start():
    try:
        os.makedirs(os.path.dirname(_SESSION_START_PATH), exist_ok=True)
        with open(_SESSION_START_PATH, "w") as f:
            json.dump({"started_at": datetime.now(timezone.utc).isoformat()}, f)
    except Exception:
        pass


def record_session_end(trigger_type: str, developer: str):
    """Calculate duration from last session_start, append to analytics.json."""
    try:
        if not os.path.exists(_SESSION_START_PATH):
            return
        with open(_SESSION_START_PATH) as f:
            start_data = json.load(f)
        started_at = datetime.fromisoformat(start_data["started_at"])
        duration_seconds = int((datetime.now(timezone.utc) - started_at).total_seconds())
        if duration_seconds < 10:
            return

        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "started_at": start_data["started_at"],
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": duration_seconds,
            "trigger": trigger_type,
            "developer": developer,
        }

        entries = _load_all()
        entries.append(entry)
        os.makedirs(os.path.dirname(_ANALYTICS_PATH), exist_ok=True)
        with open(_ANALYTICS_PATH, "w") as f:
            json.dump(entries, f, indent=2)

        os.remove(_SESSION_START_PATH)
    except Exception:
        pass


def today_summary() -> dict:
    """Return total session time and session count for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    entries = [e for e in _load_all() if e.get("date") == today]
    total_seconds = sum(e.get("duration_seconds", 0) for e in entries)
    return {
        "sessions": len(entries),
        "total_seconds": total_seconds,
        "total_human": _fmt(total_seconds),
    }


def _load_all() -> list:
    try:
        if not os.path.exists(_ANALYTICS_PATH):
            return []
        with open(_ANALYTICS_PATH) as f:
            return json.load(f)
    except Exception:
        return []


def _fmt(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}h {m}m" if m else f"{h}h"
