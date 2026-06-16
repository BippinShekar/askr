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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir

_TAG_RE = re.compile(r"<[a-z_]+[^>]*>[\s\S]*?</[a-z_]+>", re.IGNORECASE)


def _strip_tags(raw: str) -> str:
    cleaned = _TAG_RE.sub("", raw).strip()
    if not cleaned and raw.strip():
        cleaned = re.split(r"</[^>]+>", raw)[-1].strip()
    return cleaned


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    raw = payload.get("prompt", "")
    cleaned = _strip_tags(raw)

    if cleaned and cleaned != raw:
        print(json.dumps({"decision": "approve", "hookSpecificOutput": {"updatedPrompt": cleaned}}))
    else:
        print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
