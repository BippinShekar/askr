#!/usr/bin/env python3
"""
Claude Code Hook - Stop

Fires when a Claude Code session ends.
Delegates to checkpoint.create_checkpoint for handover, state update, commit+push.
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
    transcript_path = payload.get("transcript_path", "")

    from askr.session.checkpoint import create_checkpoint
    create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
    )


if __name__ == "__main__":
    main()
