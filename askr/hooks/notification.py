#!/usr/bin/env python3
"""
Claude Code Hook - Notification

Fires when Claude sends a notification to the user.
Used for HITL (human-in-the-loop) forwarding - when Claude needs
attention during an unattended session (overnight, long-running).

Phase 1: stub that logs the notification.
Phase 3: forwards to Discord when webhook is configured.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, state_path


def _log_notification(message: str, level: str):
    log_path = state_path("notifications.log")
    try:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            f.write(f"[{ts}] [{level}] {message}\n")
    except Exception:
        pass


def _send_discord(message: str, level: str):
    # Phase 3 - wire Discord webhook here
    # webhook_url = os.getenv("ASKR_DISCORD_WEBHOOK")
    # if not webhook_url:
    #     return
    # import urllib.request, urllib.parse
    # payload = json.dumps({"content": f"**Askr {level}**\n{message}"}).encode()
    # req = urllib.request.Request(webhook_url, data=payload, headers={"Content-Type": "application/json"})
    # urllib.request.urlopen(req, timeout=5)
    pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    message = payload.get("message", "")
    level = payload.get("level", "info").upper()

    if not message:
        return

    _log_notification(message, level)
    _send_discord(message, level)


if __name__ == "__main__":
    main()
