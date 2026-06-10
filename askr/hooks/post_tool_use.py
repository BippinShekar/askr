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

_LEGACY_STATS_PATH = os.path.expanduser("~/.config/askr/session_stats.json")

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


_QUOTA_REFRESH_SECS = 120  # call usage API at most once every 2 minutes


def _quota_needs_refresh(existing: dict) -> bool:
    qa = existing.get("quota_updated_at")
    if not qa:
        return True
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(qa)).total_seconds()
        return age > _QUOTA_REFRESH_SECS
    except Exception:
        return True


def _write_session_stats():
    try:
        from askr.session.monitor import get_session_stats, stats_path_for_project
        from askr.session.forecast import get_forecast

        project_path = os.getcwd()
        stats = get_session_stats(project_path)
        if not stats:
            return

        forecast  = get_forecast(stats)
        stats_path = stats_path_for_project(project_path)
        os.makedirs(os.path.dirname(stats_path), exist_ok=True)

        # Carry over quota cache from per-project file (not the legacy global)
        existing = {}
        try:
            with open(stats_path) as f:
                existing = json.load(f)
        except Exception:
            pass

        quota_pct      = existing.get("quota_pct")
        quota_reset_at = existing.get("quota_reset_at")
        quota_7d_pct   = existing.get("quota_7d_pct")
        quota_updated  = existing.get("quota_updated_at")

        if _quota_needs_refresh(existing):
            try:
                from askr.session.usage_api import get_quota_status
                qs = get_quota_status()
                if qs is not None:
                    quota_pct      = round(qs.five_hour_pct, 1)
                    quota_reset_at = qs.five_hour_reset.isoformat()
                    quota_7d_pct   = round(qs.seven_day_pct, 1)
                    quota_updated  = datetime.now(timezone.utc).isoformat()
            except Exception:
                pass

        payload = {
            "project_path": project_path,
            "context_pct": round(stats.context_pct, 4),
            "context_tokens": stats.context_tokens,
            "output_tokens": stats.output_tokens,
            "context_window": stats.context_window,
            "context_label": forecast.context_label,
            "turns": stats.turns,
            "next_trigger": forecast.next_trigger,
            "quota_pct": quota_pct,
            "quota_reset_at": quota_reset_at,
            "quota_7d_pct": quota_7d_pct,
            "quota_updated_at": quota_updated,
            "model": stats.model,
            "session_id": stats.session_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(stats_path, "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass


_GUARD_BLOCKS_PATH = os.path.expanduser("~/.config/askr/guard_blocks.json")


def _check_guard_resolution(tool_name: str, file_path: str):
    """If the completed write was to a previously-blocked file, send resolution alert."""
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return
    if not file_path:
        return
    try:
        if not os.path.exists(_GUARD_BLOCKS_PATH):
            return
        with open(_GUARD_BLOCKS_PATH) as f:
            blocks = json.load(f)
        if file_path not in blocks:
            return

        block_entry = blocks.pop(file_path)
        with open(_GUARD_BLOCKS_PATH, "w") as f:
            json.dump(blocks, f)

        issues = block_entry.get("issues", [])
        count  = block_entry.get("count", 1)

        try:
            from askr.clients.discord import send_message
            issues_text = "\n".join(f"• {i}" for i in issues) if issues else ""
            msg = (
                f"✅ **[askr guard] Resolved** — `{os.path.basename(file_path)}`\n"
                f"Blocked {count}x, then self-corrected. Write succeeded."
                + (f"\n**Original issues:**\n{issues_text}" if issues_text else "")
            )
            send_message(msg)
        except Exception:
            pass

        try:
            log_path = os.path.join(get_state_dir(), "guard_log.md")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            lines = [
                f"\n## {ts} — Resolution [RESOLVED]",
                f"**File:** `{file_path}`",
                f"Claude self-corrected after {count} block(s). Write succeeded.",
                "**Outcome:** Resolved autonomously",
                "",
            ]
            with open(log_path, "a") as f:
                f.write("\n".join(lines) + "\n")
        except Exception:
            pass
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

    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    _check_guard_resolution(tool_name, file_path)

    activity = _extract_activity(tool_name, tool_input)

    dev = load_developer()
    ts = datetime.now().strftime("%H:%M")

    if activity:
        _append_to_section(dev, f"- [{ts}] {activity}")

    _write_session_stats()


if __name__ == "__main__":
    main()
