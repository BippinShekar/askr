#!/usr/bin/env python3
"""
Claude Code Hook - PostToolUse

Fires after every tool execution.
Tracks file writes and command runs into implementation_state.md.
Also runs the session monitor + forecast and writes stats for StatusLine.
"""

import sys
import os
import json
import re
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, state_path, load_developer

_STATS_PATH = os.path.expanduser("~/.config/askr/session_stats.json")

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


def _write_session_stats():
    try:
        from askr.state.config import load_project_path
        from askr.session.monitor import get_session_stats
        from askr.session.forecast import get_forecast

        project_path = load_project_path()
        stats = get_session_stats(project_path)
        if not stats:
            return

        forecast = get_forecast(stats)
        os.makedirs(os.path.dirname(_STATS_PATH), exist_ok=True)

        payload = {
            "context_pct": round(stats.context_pct, 4),
            "context_tokens": stats.context_tokens,
            "context_window": stats.context_window,
            "turns": stats.turns,
            "next_trigger": forecast.next_trigger,
            "context_eta_turns": forecast.context_eta_turns,
            "quota_eta_minutes": round(forecast.quota_eta_minutes, 1) if forecast.quota_eta_minutes else None,
            "reset_at": forecast.reset_at.isoformat() if forecast.reset_at else None,
            "model": stats.model,
            "session_id": stats.session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(_STATS_PATH, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return

    if not os.path.isdir(get_state_dir()):
        return

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    activity = _extract_activity(tool_name, tool_input)

    dev = load_developer()
    ts = datetime.now().strftime("%H:%M")

    if activity:
        _append_to_section(dev, f"- [{ts}] {activity}")

    _write_session_stats()


if __name__ == "__main__":
    main()
