#!/usr/bin/env python3
"""
Claude Code Hook - PostToolUse

Fires after every tool execution.
Tracks file writes and command runs into implementation_state.md.
"""

import sys
import os
import json
import re
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import STATE_DIR, state_path, load_developer

_SKIP_TOOLS = {"Read", "Glob", "Grep", "LS", "WebSearch", "WebFetch", "TodoRead"}


def _extract_activity(tool_name: str, tool_input: dict) -> str | None:
    if tool_name in _SKIP_TOOLS:
        return None
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path") or tool_input.get("path", "")
        return f"Modified: {path}" if path else None
    if tool_name == "Bash":
        cmd = (tool_input.get("command") or tool_input.get("cmd", ""))[:80]
        return f"Ran: {cmd}" if cmd else None
    return None


def _append_to_section(dev: str, entry: str):
    path = state_path("implementation_state.md")
    section_start = f"<!-- section:{dev} -->"
    section_end = f"<!-- /section:{dev} -->"

    if not os.path.exists(path):
        from askr.state.writer import update_implementation_section
        update_implementation_section(
            f"### In Progress\n\n{entry}\n\n### Completed\n\n### Files Owned\n",
            dev
        )
        return

    with open(path) as f:
        content = f.read()

    if section_start not in content:
        from askr.state.writer import update_implementation_section
        update_implementation_section(
            f"### In Progress\n\n{entry}\n\n### Completed\n\n### Files Owned\n",
            dev
        )
        return

    # insert entry after "### In Progress" line within this developer's section
    pattern = rf"({re.escape(section_start)}.*?### In Progress\n)"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        insert_at = match.end()
        updated = content[:insert_at] + f"\n{entry}" + content[insert_at:]
        with open(path, "w") as f:
            f.write(updated)
    else:
        # section exists but no "### In Progress" header - append entry before section end
        updated = content.replace(
            section_end,
            f"### In Progress\n\n{entry}\n\n{section_end}"
        )
        with open(path, "w") as f:
            f.write(updated)


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return

    if not os.path.isdir(STATE_DIR):
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    activity = _extract_activity(tool_name, tool_input)
    if not activity:
        return

    dev = load_developer()
    ts = datetime.now().strftime("%H:%M")
    _append_to_section(dev, f"- [{ts}] {activity}")


if __name__ == "__main__":
    main()
