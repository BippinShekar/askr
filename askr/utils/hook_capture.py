#!/usr/bin/env python3
"""
Temporary diagnostic capture — every hook's raw payload, appended to one
bounded log. Built 2026-08-11 to answer a single open question: does Claude
Code fire ANY hook when the real 5-hour usage limit is hit and the "wait for
reset / upgrade / extra usage" menu appears?

notification.py already logs unconditionally, so if the limit-hit event
routes through Notification, this adds nothing new there — but if it routes
through a different hook (or none at all), this is the only way to find out
without guessing. Whichever hook fires closest to a live "You've hit your
limit" moment is the real detection signal for the auto-resume feature this
is scoped for; this file has no opinion about which one it'll be.

Remove once the answer is confirmed and the real automation is built against
captured data instead of a hypothesis.
"""

import json
import os
from datetime import datetime, timezone

_CAPTURE_PATH = os.path.expanduser("~/.config/askr/hook_capture.log")
_MAX_ENTRIES  = 1000  # bounded — diagnostic capture, not a permanent audit log


def capture_hook_payload(hook_name: str, payload: dict):
    """
    Append one {ts, hook, cwd, payload} entry. Never raises, never blocks —
    a hook's real work must never be delayed or broken by this. Truncates to
    the most recent _MAX_ENTRIES on every write so a multi-day capture
    window can't grow unbounded.
    """
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "hook": hook_name,
            "cwd": os.getcwd(),
            "payload": payload,
        }
        os.makedirs(os.path.dirname(_CAPTURE_PATH), exist_ok=True)
        lines = []
        if os.path.exists(_CAPTURE_PATH):
            try:
                with open(_CAPTURE_PATH) as f:
                    lines = f.readlines()
            except Exception:
                lines = []
        lines.append(json.dumps(entry) + "\n")
        if len(lines) > _MAX_ENTRIES:
            lines = lines[-_MAX_ENTRIES:]
        with open(_CAPTURE_PATH, "w") as f:
            f.writelines(lines)
    except Exception:
        pass
