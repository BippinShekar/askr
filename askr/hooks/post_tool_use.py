#!/usr/bin/env python3
"""
Claude Code Hook - PostToolUse

Fires after every tool execution.
Tracks file writes and command runs into implementation_<dev>.jsonl.
Also runs the session monitor + forecast and writes stats for StatusLine.
"""

import sys
import os
import re
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, state_path, load_developer

_LEGACY_STATS_PATH = os.path.expanduser("~/.config/askr/session_stats.json")

_SKIP_TOOLS = {"Read", "Glob", "Grep", "LS", "WebSearch", "WebFetch", "TodoRead"}


def _extract_activity(tool_name: str, tool_input: dict) -> tuple[str, str] | None:
    """Returns (entry_type, detail) for implementation_<dev>.jsonl, or None to skip."""
    if tool_name in _SKIP_TOOLS:
        return None
    if tool_name in ("Write", "Edit", "MultiEdit"):
        path = tool_input.get("file_path") or tool_input.get("path", "")
        return ("file_modified", path) if path else None
    if tool_name == "Bash":
        cmd = (tool_input.get("command") or tool_input.get("cmd", ""))[:80]
        return ("command", cmd) if cmd else None
    return None


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


def _write_session_stats(session_id: str = ""):
    try:
        from askr.session.monitor import get_session_stats, stats_path_for_session, find_project_root
        from askr.session.forecast import get_forecast

        project_path = find_project_root()
        stats = get_session_stats(project_path, session_id or None)
        if not stats:
            return

        forecast  = get_forecast(stats)
        stats_path = stats_path_for_session(project_path, stats.session_id)
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
        # Write atomically — a plain open()+dump leaves a window where a concurrent
        # reader (the IDE extension's 5s poll) can read a truncated/partial file
        # and fail to parse it. os.replace is atomic on the same filesystem.
        tmp_path = stats_path + ".tmp"
        with open(tmp_path, "w") as f:
            json.dump(payload, f, indent=2)
        os.replace(tmp_path, stats_path)
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


# ---------------------------------------------------------------------------
# Phase 3.13 S4 — real-time user-rejection detection
#
# Fast, regex-only pattern match on the most recent user message — deliberately
# NOT an LLM call, since this runs on every tool call (see stop.py's
# _extract_and_save_decisions/_DECISION_RE for the equivalent per-turn pattern
# this mirrors). Full LLM extraction with confidence scoring only happens at
# checkpoint (checkpoint.py's user_rejected_decisions schema, S2).
#
# Honest risk (roadmap.md Phase 3.13): "No, that's wrong" about the user's OWN
# code is structurally identical to rejecting a Claude proposal. A regex
# cannot tell them apart. Under-capture is fine; false positives here erode
# trust faster than missed captures — the confidence bar is kept high on
# purpose (explicit rejection phrasing only, not vague disagreement).
# ---------------------------------------------------------------------------

_REJECTION_RE = re.compile(
    r"(?i)\b("
    r"no,? that'?s wrong|don'?t do that|that'?s not (?:right|correct|it)|"
    r"not what i (?:asked|wanted|meant)|please don'?t (?:do|use) that|"
    r"stop doing that|revert (?:that|this)|undo that|"
    r"that'?s (?:incorrect|not it)|wrong approach|"
    r"no,? (?:don'?t|do not) (?:do|use) that|that is not (?:right|correct)"
    r")\b"
)

_REJECTION_CONFIDENCE = 0.75  # regex-only signal — below the 0.7+ LLM bar's ceiling, never treated as user_approved


def _read_transcript_tail(transcript_path: str, tail_bytes: int = 65536) -> list:
    """Read only the tail of the transcript for fast, bounded-cost parsing.

    PostToolUse fires on every tool call, so a full-file read (already
    accepted in stop.py's once-per-turn Stop hook) would add up fast here.
    Bounded to the last `tail_bytes` regardless of transcript size.
    """
    if not transcript_path or not os.path.exists(transcript_path):
        return []
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as f:
            if size > tail_bytes:
                f.seek(size - tail_bytes)
                f.readline()  # drop the partial line left by the seek
            raw = f.read()
        entries = []
        for line in raw.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
        return entries
    except Exception:
        return []


def _last_user_text_and_prior_assistant(entries: list) -> tuple[str, str]:
    """Returns (last_user_text, preceding_assistant_text) from tail entries.

    Tool results are logged as type "user" too (they're the next turn in the
    API sense) — skip those, we only want text the human actually typed. This
    mirrors stop.py's _turn_elapsed_seconds tool_result filter.
    """
    last_user_idx = -1
    last_user_text = ""
    for i in range(len(entries) - 1, -1, -1):
        entry = entries[i]
        if entry.get("type") != "user":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        ):
            continue
        text = ""
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "text":
                    text = b.get("text", "")
                    break
        if text and text.strip():
            last_user_idx = i
            last_user_text = text.strip()
            break

    if last_user_idx < 0:
        return "", ""

    prior_assistant_text = ""
    for i in range(last_user_idx - 1, -1, -1):
        entry = entries[i]
        if entry.get("type") != "assistant":
            continue
        content = entry.get("message", {}).get("content", [])
        if isinstance(content, list):
            for b in content:
                if isinstance(b, dict) and b.get("type") == "text":
                    t = b.get("text", "").strip()
                    if t:
                        prior_assistant_text = t
                        break
        if prior_assistant_text:
            break

    return last_user_text, prior_assistant_text


def _detect_and_save_rejection(transcript_path: str, state_dir: str, file_path: str, developer: str):
    """Scan the most recent user message for a high-confidence rejection
    signal and, if found, write it immediately to rejected_decisions.jsonl
    (don't wait for checkpoint). No-op on any failure — never blocks the hook.
    """
    try:
        entries = _read_transcript_tail(transcript_path)
        if not entries:
            return
        last_user_text, prior_assistant_text = _last_user_text_and_prior_assistant(entries)
        if not last_user_text:
            return

        sentences = re.split(r'(?<=[.!?])\s+', last_user_text)
        matched = None
        for s in sentences:
            s = s.strip()
            if 5 < len(s) < 250 and _REJECTION_RE.search(s):
                matched = s
                break
        if not matched:
            return

        what_was_proposed = prior_assistant_text[:150] if prior_assistant_text else "(see session transcript)"
        domain = file_path or "unknown"

        rejections_path = os.path.join(state_dir, "rejected_decisions.jsonl")
        from askr.state.writer import file_lock
        with file_lock(rejections_path):
            existing_text = ""
            if os.path.exists(rejections_path):
                with open(rejections_path) as f:
                    existing_text = f.read().lower()
            if matched.lower() in existing_text:
                return  # already recorded — avoid duplicate writes across multiple tool calls in the same turn

            entry = {
                "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "dev": developer,
                "what_was_proposed": what_was_proposed,
                "user_signal": matched,
                "domain": domain,
                "confidence": _REJECTION_CONFIDENCE,
                "source": "realtime_regex",
            }
            with open(rejections_path, "a") as f:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        return

    if not os.path.isdir(get_state_dir()):
        return

    tool_name       = payload.get("tool_name", "")
    tool_input      = payload.get("tool_input", {})
    session_id      = payload.get("session_id", "")
    transcript_path = payload.get("transcript_path", "")

    file_path = tool_input.get("file_path") or tool_input.get("path", "")
    _check_guard_resolution(tool_name, file_path)
    _update_edit_cursor(tool_name, tool_input, session_id)

    activity = _extract_activity(tool_name, tool_input)

    dev = load_developer()

    _detect_and_save_rejection(transcript_path, get_state_dir(), file_path, dev)

    if activity:
        entry_type, detail = activity
        from askr.state.writer import append_implementation_entry
        append_implementation_entry(entry_type, detail, dev, session_id)

    _write_session_stats(session_id)
    _maybe_refresh_constraints()

    # Heartbeat: update session registry every 5 tool uses
    if session_id:
        try:
            counter_data = {}
            if os.path.exists(_TURN_COUNTER_PATH):
                with open(_TURN_COUNTER_PATH) as f:
                    counter_data = json.load(f)
            if counter_data.get("count", 0) % 5 == 0:
                from askr.utils.retry import import_retry

                def _heartbeat():
                    from askr.session.registry import update_heartbeat
                    update_heartbeat(session_id)

                import_retry(_heartbeat)
        except Exception:
            pass


if __name__ == "__main__":
    main()
