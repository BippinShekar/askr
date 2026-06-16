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
        from askr.session.monitor import get_session_stats, stats_path_for_project, find_project_root
        from askr.session.forecast import get_forecast

        project_path = find_project_root()
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
            "user_turns": stats.user_turns,
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


_GUARD_BLOCKS_PATH   = os.path.expanduser("~/.config/askr/guard_blocks.json")
_TURN_COUNTER_PATH   = os.path.expanduser("~/.config/askr/turn_counter.json")
_CURSOR_DIR          = os.path.expanduser("~/.config/askr/cursors")
_REFRESH_EVERY_N     = 10  # inject constraint reminder every N tool uses


def _cursor_path(session_id: str) -> str:
    return os.path.join(_CURSOR_DIR, f"edit_cursor_{session_id}.json")


def _find_edit_line(tool_name: str, tool_input: dict, file_path: str) -> int:
    """Locate the exact line of the last edit by searching file content."""
    try:
        with open(file_path, "r", errors="replace") as f:
            content = f.read()

        if tool_name == "Write":
            return len(content.splitlines())

        search_str = ""
        if tool_name == "Edit":
            search_str = tool_input.get("new_string", "")
        elif tool_name == "MultiEdit":
            edits = tool_input.get("edits", [])
            if edits:
                search_str = edits[-1].get("new_string", "")

        if search_str:
            idx = content.find(search_str[:80])
            if idx >= 0:
                return content[:idx].count("\n") + 1
    except Exception:
        pass
    return 0


def _update_edit_cursor(tool_name: str, tool_input: dict, session_id: str):
    """Track file + exact line of every write op — scoped per session_id to survive parallel sessions."""
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        return
    if not session_id:
        return
    try:
        file_path = (tool_input.get("file_path") or tool_input.get("path", "")).strip()
        if not file_path or not os.path.exists(file_path):
            return

        line = _find_edit_line(tool_name, tool_input, file_path)
        path = _cursor_path(session_id)

        cursor = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    cursor = json.load(f)
            except Exception:
                cursor = {}

        cursor[file_path] = {"line": line, "ts": datetime.now().strftime("%H:%M"), "tool": tool_name}

        os.makedirs(_CURSOR_DIR, exist_ok=True)
        with open(path, "w") as f:
            json.dump(cursor, f, indent=2)
    except Exception:
        pass


def _maybe_refresh_constraints():
    """Every N tool uses, print top decisions as a reminder so they don't fade mid-session."""
    try:
        counter_data = {}
        if os.path.exists(_TURN_COUNTER_PATH):
            with open(_TURN_COUNTER_PATH) as f:
                counter_data = json.load(f)

        # Reset counter if it's a new session (state dir changed or counter stale)
        count = counter_data.get("count", 0) + 1
        counter_data["count"] = count

        os.makedirs(os.path.dirname(_TURN_COUNTER_PATH), exist_ok=True)
        with open(_TURN_COUNTER_PATH, "w") as f:
            json.dump(counter_data, f)

        if count % _REFRESH_EVERY_N != 0:
            return

        # Load top 5 decisions (most recent lines from JSONL)
        decisions_path = state_path("decisions.jsonl")
        if not os.path.exists(decisions_path):
            return
        entries = []
        with open(decisions_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    text = d.get("decision", "").strip()
                    if text:
                        entries.append(text)
                except Exception:
                    pass
        recent = entries[-5:]
        if not recent:
            return

        reminder = "askr reminder — settled decisions:\n" + "\n".join(f"  {l}" for l in recent)
        print(reminder, flush=True)
    except Exception:
        pass


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

    tool_name  = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})
    session_id = payload.get("session_id", "")

    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    _check_guard_resolution(tool_name, file_path)
    _update_edit_cursor(tool_name, tool_input, session_id)

    activity = _extract_activity(tool_name, tool_input)

    dev = load_developer()
    ts = datetime.now().strftime("%H:%M")

    if activity:
        _append_to_section(dev, f"- [{ts}] {activity}")

    _write_session_stats()
    _maybe_refresh_constraints()


if __name__ == "__main__":
    main()
