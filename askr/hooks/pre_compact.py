#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Emergency fallback. Fires when Claude is about to auto-compact.
Askr should act at ~90% context via the forecast engine.
If this fires, the forecast missed the threshold.

Generates an emergency checkpoint from whatever context is available.
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer


def _git_commit_push(developer: str):
    try:
        subprocess.run(["git", "add", get_state_dir()], capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain", get_state_dir()],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            return

        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"askr: emergency checkpoint [{developer}] {ts}"],
            capture_output=True
        )
        subprocess.run(["git", "push", "--quiet"], capture_output=True, timeout=30)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    trigger = payload.get("trigger", "auto")

    from askr.state.writer import write_handover
    write_handover(
        f"## Objective\n\nEmergency checkpoint - context was compacted ({trigger}).\n\n"
        f"## Next Step\n\nReview recent work and continue from last known state.\n\n"
        f"## Context\n\nThis checkpoint was created automatically before compaction. "
        f"Check implementation_state.md for what was in progress.",
        developer
    )

    _git_commit_push(developer)

    print(json.dumps({"custom_instructions": "State has been checkpointed. Continue from where you left off."}))


if __name__ == "__main__":
    main()
