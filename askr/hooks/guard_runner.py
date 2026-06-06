#!/usr/bin/env python3
"""
Guard Runner — spawned as a background subprocess by pre_tool_use.py.

Runs the guard check and delivers warnings via:
  1. notification.json  → IDE popup (non-blocking)
  2. Discord            → if webhook configured

This runs detached so Claude's tool execution is not blocked.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_NOTIFICATION_PATH = os.path.expanduser("~/.config/askr/notification.json")


def main():
    from askr.state.config import load_developer, get_state_dir
    from askr.session.guard import check_and_save

    developer = load_developer()
    state_dir = get_state_dir()

    if not os.path.isdir(state_dir):
        return

    result = check_and_save(developer, state_dir)
    if not result or result.get("clean", True):
        return

    issues  = result.get("issues", [])
    summary = result.get("summary", "Architectural concern detected.")
    trigger = result.get("trigger", {})
    file_path = trigger.get("file_path", "unknown file")
    reason    = trigger.get("reason", "")

    reason_label = {
        "new_file":         "New file creation",
        "batch_writes":     "Batch file edits",
        "shared_interface": "Shared interface edit",
    }.get(reason, "Implementation change")

    issues_text = "\n".join(f"• {i}" for i in issues)
    message = (
        f"**[askr guard] {reason_label}** — {os.path.basename(file_path)}\n"
        f"{summary}\n"
        f"{issues_text}"
    ).strip()

    # IDE popup
    try:
        payload = {
            "type": "guard_warning",
            "message": message,
            "summary": summary,
            "issues": issues,
            "file_path": file_path,
            "shown": False,
            "timestamp": result.get("timestamp", ""),
        }
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass

    # Discord
    try:
        from askr.clients.discord import send_message
        send_message(f"⚠️ {message}")
    except Exception:
        pass


if __name__ == "__main__":
    main()
