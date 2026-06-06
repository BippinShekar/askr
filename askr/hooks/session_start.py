#!/usr/bin/env python3
"""
Claude Code Hook - SessionStart

Fires at the start of every Claude Code session.
Pulls latest state from git, then injects project context.

Goal suggestion: if today has no goals set, calls Haiku with the last
handover to suggest 1-2 actionable goals and adds them automatically.

If started by the lifecycle daemon (launch_mode.json present), injects
the next goal as an explicit task directive.
"""

import sys
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.reader import build_context_injection
from askr.state.goals import format_for_context as goals_context
from askr.state.config import get_state_dir, load_developer

_LAUNCH_MODE_PATH = os.path.expanduser("~/.config/askr/launch_mode.json")


def git_pull():
    try:
        subprocess.run(["git", "pull", "--quiet"], capture_output=True, timeout=15)
    except Exception:
        pass


def _read_launch_mode() -> dict:
    try:
        if not os.path.exists(_LAUNCH_MODE_PATH):
            return {}
        with open(_LAUNCH_MODE_PATH) as f:
            data = json.load(f)
        if not data.get("active"):
            return {}
        ts = data.get("timestamp", "")
        if ts:
            written = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - written > timedelta(minutes=5):
                return {}
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump({"active": False}, f)
        return data
    except Exception:
        return {}


def _archive_stale_goals():
    """
    Move uncompleted goals from past-dated sections to backlog.
    Runs before goal suggestion so stale goals don't block inference.
    """
    try:
        from askr.state.goals import archive_stale_goals
        archive_stale_goals()
    except Exception:
        pass


def _notify_stale_goals():
    """
    If any timestamped goals are 6+ hours old, write a goal_check notification
    so the IDE extension surfaces them for the user to resolve.
    """
    try:
        import json as _json
        from askr.state.goals import get_stale_goals
        stale = get_stale_goals(hours=6)
        if not stale:
            return
        notification_path = os.path.expanduser("~/.config/askr/notification.json")
        goal_lines = "\n".join(f"  - {text} ({h}h ago)" for text, _, h in stale)
        payload = {
            "type": "goal_check",
            "message": f"{len(stale)} goal(s) haven't moved in 6+ hours:\n{goal_lines}",
            "goals": [{"text": t, "added": a, "hours": h} for t, a, h in stale],
            "shown": False,
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(notification_path), exist_ok=True)
        with open(notification_path, "w") as f:
            _json.dump(payload, f)
    except Exception:
        pass


def _maybe_suggest_goals(developer: str) -> list[str]:
    """
    If today has no goals, suggest 1-2 from the last handover via Haiku.
    Adds them to goals.md and returns the list (empty if skipped/failed).
    Never blocks session start — all errors are swallowed.
    """
    try:
        from askr.state.goals import load_today_goals, suggest_goals_from_handover, add_goal
        if load_today_goals():
            return []  # user already has goals — don't touch them
        suggestions = suggest_goals_from_handover(developer)
        for g in suggestions:
            add_goal(g, "today")
        return suggestions
    except Exception:
        return []


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if os.path.isdir(get_state_dir()):
        git_pull()

    try:
        from askr.state.analytics import record_session_start
        record_session_start()
    except Exception:
        pass

    developer = load_developer()
    _archive_stale_goals()
    _notify_stale_goals()
    suggested_goals = _maybe_suggest_goals(developer)

    state_context = build_context_injection()
    goals = goals_context()
    launch_mode = _read_launch_mode()

    parts = []
    if state_context:
        parts.append(state_context)
    if goals:
        parts.append(goals)

    if suggested_goals:
        goal_list = "\n".join(f"- {g}" for g in suggested_goals)
        parts.append(
            f"## Goals Auto-Suggested\n\n"
            f"No goals were set for today. Askr inferred these from your last session's handover "
            f"and added them automatically:\n\n{goal_list}\n\n"
            f"Run `askr goals` to review or `askr goal add \"...\"` to add more."
        )

    if launch_mode.get("goal"):
        goal_text = launch_mode["goal"]
        parts.append(
            f"## Active Goal (Autonomous Session)\n\n"
            f"This session was started automatically by askr after a context or quota checkpoint. "
            f"Pick up from the handover above and work on:\n\n**{goal_text}**\n\n"
            f"Continue autonomously. When done, the session will be checkpointed again."
        )

    if parts:
        print(json.dumps({"context": "\n\n".join(parts)}))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
