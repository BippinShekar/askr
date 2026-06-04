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


def _advance_launch_goal():
    """If daemon is running, update launch_mode.json with the next open goal."""
    try:
        from askr.session.lifecycle import daemon_is_running
        if not daemon_is_running():
            return
        from askr.session.lifecycle import _get_next_goal, _write_launch_mode, _LAUNCH_MODE_PATH
        import os as _os, json as _json
        active = False
        try:
            if _os.path.exists(_LAUNCH_MODE_PATH):
                with open(_LAUNCH_MODE_PATH) as f:
                    active = _json.load(f).get("active", False)
        except Exception:
            pass
        if active:
            next_goal = _get_next_goal()
            _write_launch_mode(next_goal)
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
    transcript_path = payload.get("transcript_path", "")

    from askr.session.checkpoint import create_checkpoint
    create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
    )

    _advance_launch_goal()


if __name__ == "__main__":
    main()
