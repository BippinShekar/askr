#!/usr/bin/env python3
"""
Claude Code Hook - UserPromptSubmit

Fires before Claude processes each user message.
Strips IDE metadata tags from the prompt before Claude sees it.
(current_task_<dev>.md removed — redundant with handover JSON.)
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir

_TAG_RE = re.compile(r"<[a-z_]+[^>]*>[\s\S]*?</[a-z_]+>", re.IGNORECASE)

_TURN_START_DIR = os.path.expanduser("~/.config/askr/turn_starts")


def _strip_tags(raw: str) -> str:
    cleaned = _TAG_RE.sub("", raw).strip()
    if not cleaned and raw.strip():
        cleaned = re.split(r"</[^>]+>", raw)[-1].strip()
    return cleaned


def _signal_turn_started(session_id: str):
    """
    Mark that this session has just been given a new prompt to work on. Read by
    lifecycle.py's idle-trigger check (_turn_currently_active) so a turn that is
    actively in progress right now never gets mistaken for "quiet for 10 minutes"
    just because it's been over IDLE_TRIGGER_SECS since the PREVIOUS turn ended.
    """
    if not session_id:
        return
    try:
        os.makedirs(_TURN_START_DIR, exist_ok=True)
        with open(os.path.join(_TURN_START_DIR, f"{session_id}.json"), "w") as f:
            json.dump({"started_at": datetime.utcnow().isoformat() + "Z"}, f)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    _signal_turn_started(payload.get("session_id", ""))

    raw = payload.get("prompt", "")
    cleaned = _strip_tags(raw)

    if cleaned and cleaned != raw:
        print(json.dumps({
            "decision": "approve",
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "updatedPrompt": cleaned,
            },
        }))
    else:
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
