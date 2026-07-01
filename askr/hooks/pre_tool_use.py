#!/usr/bin/env python3
"""
Claude Code Hook - PreToolUse

Fires before every tool execution. On significant write operations runs a
synchronous guard check. If architectural issues are found, blocks the write
and surfaces the reason directly to Claude so it can self-correct.

Significance thresholds:
  - First new file creation (Write to a path that doesn't exist yet)
  - 3rd file edit in a session (batch implementation detected)
  - Edit to a file listed as a core/shared interface in architecture.md

Blocking: outputs {"decision": "block", "reason": "..."} + exits 2 when
guard detects a real architectural contradiction. Exits 0 (allow) otherwise.
"""

import sys
import os
import json
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

_GUARD_SESSION_PATH  = os.path.expanduser("~/.config/askr/guard_session.json")
_GUARD_BLOCKS_PATH   = os.path.expanduser("~/.config/askr/guard_blocks.json")
_GUARD_COOLDOWN_SECS = 300   # don't re-trigger within 5 minutes
_BLOCK_TTL_SECS      = 86400 # expire block entries after 24 hours
_BATCH_THRESHOLD     = 3     # N file edits before a batch trigger fires
_ESCAPE_HATCH_COUNT  = 2     # allow through + escalate after this many consecutive blocks


def _load_session() -> dict:
    try:
        if os.path.exists(_GUARD_SESSION_PATH):
            with open(_GUARD_SESSION_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {"write_count": 0, "last_trigger_at": None, "session_date": _today()}


def _save_session(data: dict):
    try:
        os.makedirs(os.path.dirname(_GUARD_SESSION_PATH), exist_ok=True)
        with open(_GUARD_SESSION_PATH, "w") as f:
            json.dump(data, f)
    except Exception:
        pass


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _in_cooldown(session: dict) -> bool:
    last = session.get("last_trigger_at")
    if not last:
        return False
    try:
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
        return elapsed < _GUARD_COOLDOWN_SECS
    except Exception:
        return False


def _is_new_file(path: str) -> bool:
    if not path:
        return False
    return not os.path.exists(path)


def _is_shared_interface(path: str) -> bool:
    """Check if the file is flagged as a core/shared interface in architecture.md."""
    if not path:
        return False
    try:
        from askr.state.config import state_path
        arch_path = state_path("architecture.md")
        if not os.path.exists(arch_path):
            return False
        with open(arch_path) as f:
            content = f.read()
        filename = os.path.basename(path)
        lower = content.lower()
        name_lower = filename.lower()
        idx = lower.find(name_lower)
        if idx == -1:
            return False
        surrounding = lower[max(0, idx - 80):idx + 80]
        return any(k in surrounding for k in ("core", "shared", "interface", "api", "entry"))
    except Exception:
        return False


def _load_blocks() -> dict:
    try:
        if os.path.exists(_GUARD_BLOCKS_PATH):
            with open(_GUARD_BLOCKS_PATH) as f:
                blocks = json.load(f)
            # Expire stale entries — a block older than 24h is no longer actionable
            now = datetime.now(timezone.utc)
            expired = [
                path for path, entry in blocks.items()
                if _block_is_expired(entry, now)
            ]
            if expired:
                for path in expired:
                    del blocks[path]
                _save_blocks(blocks)
            return blocks
    except Exception:
        pass
    return {}


def _block_is_expired(entry: dict, now: datetime) -> bool:
    last_blocked = entry.get("last_blocked")
    if not last_blocked:
        return False
    try:
        age = (now - datetime.fromisoformat(last_blocked)).total_seconds()
        return age > _BLOCK_TTL_SECS
    except Exception:
        return False


def _save_blocks(blocks: dict):
    try:
        os.makedirs(os.path.dirname(_GUARD_BLOCKS_PATH), exist_ok=True)
        with open(_GUARD_BLOCKS_PATH, "w") as f:
            json.dump(blocks, f)
    except Exception:
        pass


def _block_tool(reason: str):
    """Output block decision to stdout and exit 2 to prevent the tool from running."""
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(2)


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)

    tool_name = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {})

    # Only care about write/edit operations
    if tool_name not in ("Write", "Edit", "MultiEdit"):
        sys.exit(0)

    try:
        from askr.state.config import get_state_dir
        if not os.path.isdir(get_state_dir()):
            sys.exit(0)
    except Exception:
        sys.exit(0)

    file_path = tool_input.get("file_path") or tool_input.get("path", "")

    # Skip askr's own state files — guard is for project code, not state artifacts
    if "askr_state" in file_path or ".claude" in file_path:
        sys.exit(0)

    # Cross-repo boundary check: block writes to paths outside the current project root.
    # Prevents a session in repo A from silently modifying repo B via handover continuation.
    try:
        from askr.state.config import get_state_dir as _gsd
        project_root = os.path.dirname(os.path.normpath(_gsd()))
        abs_file = os.path.realpath(os.path.abspath(file_path))
        abs_root = os.path.realpath(project_root)
        if abs_file and abs_root and not abs_file.startswith(abs_root + os.sep) and abs_file != abs_root:
            _block_tool(
                f"Cross-repo write blocked: {file_path} is outside the current project root "
                f"({project_root}). This session is scoped to that project. "
                f"Open a session in the target repository to make changes there."
            )
    except Exception:
        pass

    session = _load_session()
    blocks  = _load_blocks()

    # Reset counter if it's a new day
    if session.get("session_date") != _today():
        session = {"write_count": 0, "last_trigger_at": None, "session_date": _today()}

    # Previously-blocked files bypass the cooldown so retries are always checked
    previously_blocked = file_path in blocks
    if _in_cooldown(session) and not previously_blocked:
        sys.exit(0)

    session["write_count"] = session.get("write_count", 0) + 1

    trigger_reason = None

    if tool_name == "Write" and _is_new_file(file_path):
        trigger_reason = "new_file"
    elif session["write_count"] == _BATCH_THRESHOLD:
        trigger_reason = "batch_writes"
    elif _is_shared_interface(file_path):
        trigger_reason = "shared_interface"
    elif previously_blocked:
        # Retry of a previously-blocked file — re-check regardless of standard triggers
        trigger_reason = blocks[file_path].get("trigger_reason", "retry")

    if trigger_reason:
        # Escape hatch: if blocked too many times, allow through and escalate
        block_count = blocks.get(file_path, {}).get("count", 0)
        if block_count >= _ESCAPE_HATCH_COUNT:
            _on_escape_hatch(file_path, blocks[file_path])
            del blocks[file_path]
            _save_blocks(blocks)
            _save_session(session)
            sys.exit(0)

        trigger = {
            "reason": trigger_reason,
            "tool": tool_name,
            "file_path": file_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        result = _run_guard(trigger)

        if not result.get("clean", True):
            # Do NOT update last_trigger_at — blocked writes must not enter cooldown
            # so the corrected retry will also be checked.
            blocks.setdefault(file_path, {"count": 0})
            blocks[file_path]["count"] = blocks[file_path].get("count", 0) + 1
            blocks[file_path]["last_blocked"] = datetime.now(timezone.utc).isoformat()
            blocks[file_path]["trigger_reason"] = trigger_reason
            blocks[file_path]["issues"] = result.get("issues", [])
            _save_blocks(blocks)
            _save_session(session)
            _on_block(result, file_path, trigger_reason)
            # _on_block calls _block_tool which exits — nothing below runs on block
        else:
            session["last_trigger_at"] = datetime.now(timezone.utc).isoformat()

    _save_session(session)
    sys.exit(0)


def _run_guard(trigger: dict) -> dict:
    """Run guard check synchronously. Returns {"clean": True} on any failure."""
    try:
        from askr.state.config import load_developer, get_state_dir
        from askr.session.guard import run_guard_check
        developer = load_developer()
        state_dir = get_state_dir()
        return run_guard_check(trigger, developer, state_dir)
    except Exception:
        return {"clean": True}


def _on_block(result: dict, file_path: str, trigger_reason: str):
    """Send Discord alert, log the block, then emit the block signal. Does not return (exits 2)."""
    issues  = result.get("issues", [])
    summary = result.get("summary", "Architectural issue detected.")

    reason_label = {
        "new_file":         "New file creation",
        "batch_writes":     "Batch file edits",
        "shared_interface": "Shared interface edit",
    }.get(trigger_reason, "Implementation change")

    issues_text = "\n".join(f"• {i}" for i in issues) if issues else ""
    block_reason = (
        f"Guard blocked: {summary}"
        + (f"\n\n{issues_text}" if issues_text else "")
        + "\n\nRevise your approach to address these architectural concerns before proceeding."
        + "\n\nIMPORTANT: Do NOT write any entry to decisions.jsonl or failed_approaches.md based on this guard block. Guard blocks are operational events, not architectural decisions. Writing guard concerns as decisions creates a self-reinforcing loop."
    )

    _send_discord_block_alert(file_path, reason_label, summary, issues)
    _append_guard_log_block(file_path, reason_label, summary, issues)
    _block_tool(block_reason)


def _send_discord_block_alert(file_path: str, reason_label: str, summary: str, issues: list):
    try:
        from askr.clients.discord import send_message
        issues_text = "\n".join(f"• {i}" for i in issues) if issues else ""
        msg = (
            f"⛔ **[askr guard] Blocked** — {reason_label}: `{os.path.basename(file_path)}`\n"
            f"{summary}"
            + (f"\n{issues_text}" if issues_text else "")
        )
        send_message(msg)
    except Exception:
        pass


def _append_guard_log_block(file_path: str, reason_label: str, summary: str, issues: list):
    try:
        from askr.state.config import get_state_dir
        from datetime import datetime
        log_path = os.path.join(get_state_dir(), "guard_log.md")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines = [f"\n## {ts} — {reason_label} [BLOCKED]"]
        lines.append(f"**File:** `{file_path}`")
        lines.append(f"**Summary:** {summary}")
        if issues:
            lines.append("**Issues:**")
            lines.extend(f"- {i}" for i in issues)
        lines.append("**Outcome:** Write blocked — awaiting Claude correction")
        lines.append("")

        header = ""
        if not os.path.exists(log_path):
            header = "# Guard Log\n\nAppend-only log of architectural warnings raised during implementation.\n"

        with open(log_path, "a") as f:
            if header:
                f.write(header)
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


def _on_escape_hatch(file_path: str, block_entry: dict):
    """Blocked too many times — allow the write but escalate to Discord as unresolved."""
    count  = block_entry.get("count", _ESCAPE_HATCH_COUNT)
    issues = block_entry.get("issues", [])
    try:
        from askr.clients.discord import send_message
        issues_text = "\n".join(f"• {i}" for i in issues) if issues else ""
        msg = (
            f"🚨 **[askr guard] Unresolved** — `{os.path.basename(file_path)}`\n"
            f"Blocked {count}x without correction. Allowing write through.\n"
            f"**Requires manual review.**"
            + (f"\n{issues_text}" if issues_text else "")
        )
        send_message(msg)
    except Exception:
        pass

    try:
        from askr.state.config import get_state_dir
        log_path = os.path.join(get_state_dir(), "guard_log.md")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"\n## {ts} — Escape hatch [UNRESOLVED]",
            f"**File:** `{file_path}`",
            f"Blocked {count}x — Claude did not self-correct. Write allowed through.",
            "**Outcome:** Escalated — requires manual review",
            "",
        ]
        header = ""
        if not os.path.exists(log_path):
            header = "# Guard Log\n\nAppend-only log of architectural warnings raised during implementation.\n"
        with open(log_path, "a") as f:
            if header:
                f.write(header)
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
