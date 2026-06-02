#!/usr/bin/env python3
"""
Claude Code Hook - UserPromptSubmit

Fires before Claude processes each user message.
Updates current_task file with the active objective.
"""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.writer import write_current_task
from askr.state.config import STATE_DIR


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    if not os.path.isdir(STATE_DIR):
        print(json.dumps({"decision": "approve"}))
        return

    prompt = payload.get("prompt", "").strip()

    if prompt and len(prompt) > 10:
        first_line = prompt.split("\n")[0][:200]
        write_current_task(first_line)

    print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
