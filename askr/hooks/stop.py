#!/usr/bin/env python3
"""
Claude Code Hook - Stop

Fires when a Claude Code session ends.
Delegates to checkpoint.create_checkpoint for handover, state update, commit+push.
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer


def _update_allowed_tools(transcript_path: str):
    """Extract tool names from session JSONL and persist to allowedTools + permissions.allow."""
    if not transcript_path or not os.path.exists(transcript_path):
        return

    tools_used = set()
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "")
                            if name:
                                tools_used.add(name)
    except Exception:
        return

    if not tools_used:
        return

    project_dir = os.path.join(os.getcwd(), ".claude")

    try:
        settings_path = os.path.join(project_dir, "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
        else:
            settings = {}

        existing = set(settings.get("allowedTools", []))
        if tools_used - existing:
            settings["allowedTools"] = sorted(existing | tools_used)
            os.makedirs(project_dir, exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)
    except Exception:
        pass

    # permissions.allow in settings.local.json is what actually silences prompts
    try:
        local_path = os.path.join(project_dir, "settings.local.json")
        if os.path.exists(local_path):
            with open(local_path) as f:
                local = json.load(f)
        else:
            local = {}
        perms = local.setdefault("permissions", {})
        existing_allow = set(perms.get("allow", []))
        if tools_used - existing_allow:
            perms["allow"] = sorted(existing_allow | tools_used)
            os.makedirs(project_dir, exist_ok=True)
            with open(local_path, "w") as f:
                json.dump(local, f, indent=2)
    except Exception:
        pass


def _advance_launch_goal():
    """If daemon is running, update launch_mode.json with the next open goal."""
    try:
        from askr.session.lifecycle import daemon_is_running
        if not daemon_is_running():
            return
        from askr.session.lifecycle import _get_next_goal, _write_launch_mode, _LAUNCH_MODE_PATH
        import os as _os, json as _json
        active = False
        try:
            if _os.path.exists(_LAUNCH_MODE_PATH):
                with open(_LAUNCH_MODE_PATH) as f:
                    active = _json.load(f).get("active", False)
        except Exception:
            pass
        if active:
            next_goal = _get_next_goal()
            _write_launch_mode(next_goal)
    except Exception:
        pass


def _write_relaunch_notification_if_pending(checkpoint_result: dict) -> bool:
    """
    If the daemon flagged a pending checkpoint, write the re-launch notification
    using the already-completed stop checkpoint result.

    The stop checkpoint (create_checkpoint) ALWAYS runs first — this function
    only decides whether to open a new autonomous session afterward.

    - trigger==context: write IDE notification to open a new session immediately
    - trigger==quota:   write notification informing quota is high; daemon waits
    """
    _CHECKPOINT_PENDING = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
    _NOTIFICATION_PATH  = os.path.expanduser("~/.config/askr/notification.json")

    try:
        if not os.path.exists(_CHECKPOINT_PENDING):
            return False
        with open(_CHECKPOINT_PENDING) as f:
            pending = json.load(f)
        os.remove(_CHECKPOINT_PENDING)
    except Exception:
        return False

    # If the daemon wrote the flag more than 5 min ago and the session continued
    # past it, treat the flag as stale — the user finished their work voluntarily.
    try:
        import datetime as _dt_check
        written_at = pending.get("timestamp", "")
        if written_at:
            written = _dt_check.datetime.fromisoformat(written_at)
            age_s = (_dt_check.datetime.now(_dt_check.timezone.utc) - written).total_seconds()
            if age_s > 300:
                return False
    except Exception:
        pass

    try:
        from askr.session.lifecycle import (
            _get_next_goal, _write_launch_mode, _load_allowed_tools,
            _infer_direction, _read_session_arc,
        )
        from askr.state.config import load_developer
        import datetime as _dt

        trigger = pending.get("trigger", "context")

        next_goal = _get_next_goal()
        _write_launch_mode(next_goal)

        project_path  = os.getcwd()
        allowed_tools = _load_allowed_tools(project_path)
        now           = _dt.datetime.now(_dt.timezone.utc).isoformat()

        if trigger == "quota":
            quota_pct = pending.get("quota_pct", 0)
            pct_str   = f"{round(quota_pct)}%" if quota_pct else "high"
            payload = {
                "type": "quota",
                "message": f"Quota at {pct_str} — state saved. Askr will resume after reset.",
                "goal": next_goal,
                "shown": False,
                "timestamp": now,
            }
        else:
            pct       = pending.get("context_pct", 0)
            pct_str   = f"{round(pct * 100)}%"
            developer = load_developer()

            # Build direction from ground-truth signals, not from handover speculation
            direction = _infer_direction(project_path)
            confidence = direction["confidence"]

            if confidence >= 0.70:
                # High-confidence: session prompt leads with the inferred direction.
                # The handover provides context; direction provides the directive.
                arc = _read_session_arc(developer) if direction["signal_source"] == "git_momentum" else ""
                arc_part = f" Context from recent sessions: {arc}" if arc else ""
                stop_prompt = (
                    f"Continue work on: {direction['direction']}. "
                    f"Read the handover file for context on where the last session left off.{arc_part} "
                    f"Work autonomously."
                )
            else:
                # Low-confidence: session arc as supplementary context, but gate fires in S6
                arc = _read_session_arc(developer)
                arc_part = f" Recent session arc: {arc}." if arc else ""
                stop_prompt = (
                    f"Read the handover file.{arc_part} "
                    f"Before starting any work, summarise what you plan to do and wait "
                    f"for confirmation from the user."
                )

            payload = {
                "type": "context",
                "message": f"Context at {pct_str} — state saved to git. Opening new chat.",
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": stop_prompt,
                "direction_confidence": confidence,
                "direction_signal": direction["signal_source"],
                "shown": False,
                "timestamp": now,
            }

        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)

        return True
    except Exception:
        return False


_DECISION_RE = __import__('re').compile(
    r"(?i)\b("
    r"we(?:'ll| will| should) use|going with|decided? to|the (?:approach|solution|fix) is|"
    r"(?:will|won't) use|should not|must not|instead (?:use|of)|the correct (?:approach|fix)|"
    r"we(?:'re| are) using|implemented? (?:as|using|with)|the right (?:approach|way)"
    r")\b"
)


def _extract_and_save_decisions(transcript_path: str, state_dir: str):
    """Keyword-detect settled decisions in Claude's last response and append to decisions.md."""
    if not transcript_path or not os.path.exists(transcript_path):
        return
    try:
        import re
        lines = []
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except Exception:
                        pass

        # Collect text from all assistant blocks in the last turn
        # (entries after the final user message)
        last_user_idx = -1
        for i, entry in enumerate(lines):
            if entry.get("type") == "user":
                last_user_idx = i

        text_parts = []
        for entry in lines[last_user_idx + 1:] if last_user_idx >= 0 else lines:
            if entry.get("type") == "assistant":
                for block in entry.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

        full_text = " ".join(text_parts)
        if not full_text.strip():
            return

        # Extract sentences containing decision language
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        decisions = []
        for s in sentences:
            s = re.sub(r'\*+', '', s).strip()
            if 20 < len(s) < 250 and _DECISION_RE.search(s):
                decisions.append(s)
            if len(decisions) >= 5:
                break

        if not decisions:
            return

        decisions_path = os.path.join(state_dir, "decisions.md")
        ts = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
        header = ""
        if not os.path.exists(decisions_path):
            header = "# Decisions\n\nAuto-captured from session activity. Edit freely.\n\n"
        with open(decisions_path, "a") as f:
            if header:
                f.write(header)
            for d in decisions:
                f.write(f"[{ts}] {d}\n")
    except Exception:
        pass


def _broadcast_session_end(developer: str, completed_goals: list, project_path: str, duration_seconds: int = 0, autonomous: bool = False):
    try:
        from askr.session.cost import get_session_cost_summary, record_checkpoint_cost
        from askr.session.report_image import session_card
        from askr.session.checkpoint import _context_history_for_session
        from askr.clients.discord import send_file, send_message

        # collect files changed
        files_changed = []
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD~1", "--name-only"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            files_changed = [
                f for f in res.stdout.strip().splitlines()
                if not f.startswith("askr_state/")
            ]
        except Exception:
            pass

        cost_summary = get_session_cost_summary(project_path)
        record_checkpoint_cost("stop", developer, cost_summary)

        duration    = duration_seconds
        context_h   = _context_history_for_session(project_path)

        img_path = session_card(
            trigger_type="stop",
            developer=developer,
            cost_summary=cost_summary,
            duration_seconds=duration,
            goals_completed=completed_goals,
            files_changed=files_changed,
            context_history=context_h,
            autonomous=autonomous,
            project_path=project_path,
        )

        caption = f"**[askr] Session ended** — {developer}"
        if completed_goals:
            caption += "\n" + "  ".join(f"✓ {g}" for g in completed_goals[:3])

        if img_path:
            sent = send_file(img_path, caption)
            try:
                os.remove(img_path)
            except Exception:
                pass
            if not sent:
                _broadcast_session_text(developer, completed_goals, project_path)
        else:
            _broadcast_session_text(developer, completed_goals, project_path)
    except Exception:
        _broadcast_session_text(developer, completed_goals, project_path)


def _broadcast_session_text(developer: str, completed_goals: list, project_path: str):
    """Text-only fallback for when image generation fails."""
    try:
        from askr.clients.discord import send_message
        lines = [f"**[askr] Session ended** — {developer}"]
        if completed_goals:
            lines.append("**Goals completed:**")
            lines.extend(f"✓ {g}" for g in completed_goals)
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "--name-only"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            files = [f for f in result.stdout.strip().splitlines() if not f.startswith("askr_state/")]
            if files:
                lines.append("**Files changed:**")
                lines.extend(f"  {f}" for f in files[:10])
                if len(files) > 10:
                    lines.append(f"  …and {len(files) - 10} more")
            msg_result = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            commit_msg = msg_result.stdout.strip()
            if commit_msg and not commit_msg.startswith("askr:"):
                lines.append(f"**Last commit:** {commit_msg}")
        except Exception:
            pass
        if len(lines) > 1:
            send_message("\n".join(lines))
    except Exception:
        pass


def _was_autonomous() -> bool:
    """True if this session was launched by askr (goal_launch or context trigger)."""
    try:
        from askr.session.lifecycle import _LAUNCH_MODE_PATH
        if os.path.exists(_LAUNCH_MODE_PATH):
            with open(_LAUNCH_MODE_PATH) as f:
                return json.load(f).get("active", False)
    except Exception:
        pass
    return False


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")
    autonomous = _was_autonomous()
    _update_allowed_tools(transcript_path)
    _extract_and_save_decisions(transcript_path, get_state_dir())

    # Always run the authoritative stop checkpoint first — this is ground truth.
    # _write_relaunch_notification_if_pending uses its result but never replaces it.
    from askr.session.checkpoint import create_checkpoint
    result = create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
    )

    completed_goals = result.get("completed_goals", [])
    duration_seconds = result.get("duration_seconds", 0)

    # If daemon flagged a pending checkpoint, write the re-launch notification now.
    # Return early so we don't also send a session-end card — the new session handles continuity.
    if _write_relaunch_notification_if_pending(result):
        _advance_launch_goal()
        return

    # Only send a card for meaningful stops — goals completed or session ran >5 min.
    # Suppresses noise from casual conversation turns and quick tests.
    if completed_goals or duration_seconds >= 300:
        _broadcast_session_end(developer, completed_goals, os.getcwd(), duration_seconds, autonomous)

    _advance_launch_goal()


if __name__ == "__main__":
    main()
