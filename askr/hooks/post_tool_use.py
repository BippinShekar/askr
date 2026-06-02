#!/usr/bin/env python3
"""
Claude Code Hook - PostToolUse

Fires after every tool execution.
Tracks file writes, command runs, and test results into implementation_state.md.
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.writer import update_implementation_section, append_decision
from askr.state.reader import _read
from askr.state.config import STATE_DIR, state_path

_SKIP_TOOLS = {"Read", "Glob", "Grep", "LS", "WebSearch", "WebFetch"}


def _extract_activity(tool_name: str, tool_input: dict, tool_response) -> str | None:
    if tool_name in _SKIP_TOOLS:
        return None

    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path") or tool_input.get("path", "")
        if path:
            return f"Modified: {path}"

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")[:80]
        if cmd:
            return f"Ran: {cmd}"

    return None


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return

    if not os.path.isdir(STATE_DIR):
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    tool_response = payload.get("tool_response", "")

    activity = _extract_activity(tool_name, tool_input, tool_response)
    if not activity:
        return

    impl_path = state_path("implementation_state.md")
    existing = _read(impl_path)

    timestamp = datetime.now().strftime("%H:%M")
    new_entry = f"- [{timestamp}] {activity}"

    if "### In Progress" in existing:
        from askr.state.config import load_developer
        dev = load_developer()
        section_marker = f"<!-- section:{dev} -->"
        if section_marker in existing:
            lines = existing.split("\n")
            in_progress_idx = None
            in_section = False
            for i, line in enumerate(lines):
                if section_marker in line:
                    in_section = True
                if in_section and "### In Progress" in line:
                    in_progress_idx = i
                    break
            if in_progress_idx is not None:
                lines.insert(in_progress_idx + 1, new_entry)
                with open(impl_path, "w") as f:
                    f.write("\n".join(lines))
                return

    from askr.state.config import load_developer
    dev = load_developer()
    update_implementation_section(f"### In Progress\n\n{new_entry}\n\n### Completed\n\n[Nothing yet]\n\n### Files Owned\n\n[None]", dev)


if __name__ == "__main__":
    main()
