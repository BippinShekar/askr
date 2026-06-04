#!/usr/bin/env python3
"""
Claude Code Hook - SessionStart

Fires at the start of every Claude Code session.
Pulls latest state from git, then injects project context.
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
from askr.state.config import get_state_dir

_LAUNCH_MODE_PATH = os.path.expanduser("~/.config/askr/launch_mode.json")


def git_pull():
    try:
        subprocess.run(
            ["git", "pull", "--quiet"],
            capture_output=True,
            timeout=15
        )
    except Exception:
        pass


def _read_launch_mode() -> dict:
    """
    Returns launch mode dict if daemon started this session recently (within 5 min).
    Clears the file after reading so it doesn't persist across manual sessions.
    """
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
            age = datetime.now(timezone.utc) - written
            if age > timedelta(minutes=5):
                return {}  # stale - manual session, not daemon-started
        # consume the flag so next manual session isn't affected
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump({"active": False}, f)
        return data
    except Exception:
        return {}


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if os.path.isdir(get_state_dir()):
        git_pull()

    state_context = build_context_injection()
    goals = goals_context()
    launch_mode = _read_launch_mode()

    parts = []
    if state_context:
        parts.append(state_context)
    if goals:
        parts.append(goals)

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
