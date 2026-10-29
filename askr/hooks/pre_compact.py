#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Observe-only. Logs each compaction to daemon.log and lets Claude Code compact.

This hook used to SIGKILL the session to stop compaction, then run an
emergency checkpoint and open a companion session. Dropped 2026-10-29:
- 11 of the last 12 kills hit sessions Claude Code was compacting in the
  background ~54 min after their last turn ended — idle, nothing to protect.
- The kill target came from a cwd-based pid guess, which SIGKILLed a
  different, actively working session in the same repo (2026-10-27).
- Compaction usually finished anyway; the kill only cost the user their
  terminal.
Context runway is handled by the daemon's Trigger A companion session
instead (2026-06-17 decision: open a companion, never kill the live session).
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir

_DAEMON_LOG_PATH = os.path.expanduser("~/.config/askr/daemon.log")
QUOTA_HIGH       = 70.0  # treat as quota-exhausted if above this (read by stop.py)


def _log_compaction(session_id: str, trigger: str, project_path: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        os.makedirs(os.path.dirname(_DAEMON_LOG_PATH), exist_ok=True)
        with open(_DAEMON_LOG_PATH, "a") as f:
            f.write(f"[{ts}] PreCompact: allowing {trigger or '?'} compaction "
                    f"session={session_id or '?'} [{project_path}]\n")
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    from askr.utils.hook_capture import capture_hook_payload
    capture_hook_payload("PreCompact", payload)

    if not os.path.isdir(get_state_dir()):
        return

    transcript_path = payload.get("transcript_path", "")
    session_id = payload.get("session_id") or (
        os.path.basename(transcript_path).replace(".jsonl", "") if transcript_path else "")

    from askr.session.monitor import find_project_root
    _log_compaction(session_id, payload.get("trigger", ""), find_project_root())


if __name__ == "__main__":
    main()
