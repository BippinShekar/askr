#!/usr/bin/env python3
"""
Claude Code Hook - UserPromptSubmit

Fires before Claude processes each user message.
Extracts the actual user intent (strips IDE metadata tags) and
appends it to current_task file with a timestamp.
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, state_path, load_developer

_TAG_RE = re.compile(r"<[a-z_]+[^>]*>[\s\S]*?</[a-z_]+>", re.IGNORECASE)
_MIN_LEN = 8
_MAX_LEN = 200
_KEEP_ENTRIES = 5


def _extract_intent(raw: str) -> str:
    """Strip IDE metadata tags and return the actual user text."""
    cleaned = _TAG_RE.sub("", raw).strip()
    if not cleaned and raw.strip():
        # Whole prompt was a tag - try to get text after last closing tag
        after = re.split(r"</[^>]+>", raw)[-1].strip()
        cleaned = after
    lines = [l.strip() for l in cleaned.split("\n") if l.strip()]
    return lines[0][:_MAX_LEN] if lines else ""


def _update_current_task(intent: str, developer: str):
    path = state_path(f"current_task_{developer}.md")
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not os.path.exists(path):
        content = (
            f"# Current Task: {developer}\n\n"
            f"## Recent Objectives\n\n"
            f"- [{ts}] {intent}\n"
        )
    else:
        with open(path) as f:
            content = f.read()

        entry = f"- [{ts}] {intent}"

        if "## Recent Objectives" in content:
            lines = content.split("\n")
            insert_at = next(
                (i + 1 for i, l in enumerate(lines) if "## Recent Objectives" in l),
                len(lines)
            )
            lines.insert(insert_at, entry)

            # Keep only the last N entries
            objective_lines = [
                (i, l) for i, l in enumerate(lines)
                if re.match(r"^- \[\d{4}-\d{2}-\d{2}", l)
            ]
            if len(objective_lines) > _KEEP_ENTRIES:
                for idx, _ in objective_lines[:-_KEEP_ENTRIES]:
                    lines[idx] = None
                lines = [l for l in lines if l is not None]

            content = "\n".join(lines)
        else:
            content += f"\n## Recent Objectives\n\n{entry}\n"

    with open(path, "w") as f:
        f.write(content)


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"decision": "approve"}))
        return

    if not os.path.isdir(get_state_dir()):
        print(json.dumps({"decision": "approve"}))
        return

    raw = payload.get("prompt", "")
    intent = _extract_intent(raw)

    if intent and len(intent) >= _MIN_LEN:
        developer = load_developer()
        _update_current_task(intent, developer)

    print(json.dumps({"decision": "approve"}))


if __name__ == "__main__":
    main()
