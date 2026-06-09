#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Emergency fallback — fires when Claude is about to auto-compact the context.
The 65% daemon trigger should prevent this from ever firing in normal operation.
When it does fire (e.g. single-turn extended-thinking jump from <65% to 100%+),
we checkpoint, kill the process, and let the Stop hook handle the clean restart.
PreCompact cannot block compaction via its return value, so killing the process
is the only way to guarantee a fresh session instead of a compressed one.
"""

import sys
import os
import json
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer

_CLAUDE_PID_PATH    = os.path.expanduser("~/.config/askr/claude_session.pid")
_CHECKPOINT_PENDING = os.path.expanduser("~/.config/askr/checkpoint_pending.json")


def _read_claude_pid():
    try:
        with open(_CLAUDE_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


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

    # Kill the Claude process so the Stop hook fires and handles a clean restart
    # via checkpoint_pending.json → notification.json → extension opens new session.
    # If the PID isn't tracked (e.g. manually started session), fall back to the
    # old behaviour — compaction happens but state is at least saved.
    pid = _read_claude_pid()
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        # Return nothing — process is dying, output doesn't matter
        return

    # Fallback: no PID, can't kill — at least state is saved
    print(json.dumps({
        "custom_instructions": "Askr has checkpointed state to git. A new session will resume from the handover."
    }))


if __name__ == "__main__":
    main()
