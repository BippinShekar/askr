#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Emergency fallback. Fires when Claude is about to auto-compact.
Askr should act at ~90% context via the forecast engine before this fires.
If this fires, the forecast missed the threshold.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()

    from askr.session.checkpoint import create_checkpoint
    create_checkpoint(
        trigger_type="emergency",
        developer=developer,
        transcript_path=payload.get("transcript_path", ""),
    )

    print(json.dumps({"custom_instructions": "State has been checkpointed. Continue from where you left off."}))


if __name__ == "__main__":
    main()
