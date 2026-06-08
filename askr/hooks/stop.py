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
    """Extract tool names from session JSONL and add any new ones to settings.json allowedTools."""
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

    settings_path = os.path.join(os.getcwd(), ".claude", "settings.json")

    try:
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
        else:
            settings = {}

        existing = set(settings.get("allowedTools", []))
        new_tools = tools_used - existing
        if new_tools:
            settings["allowedTools"] = sorted(existing | tools_used)
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)
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


def _handle_pending_checkpoint(developer: str, transcript_path: str):
    """
    If the daemon flagged a context checkpoint, execute it now that the
    current exchange is complete. Spawns a new session via the IDE notification.
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

    try:
        from askr.session.checkpoint import create_checkpoint
        from askr.session.lifecycle import _get_next_goal, _write_launch_mode

        result = create_checkpoint(
            trigger_type="context",
            developer=developer,
            transcript_path=transcript_path,
        )

        next_goal = _get_next_goal()
        _write_launch_mode(next_goal)

        pct = pending.get("context_pct", 0)
        pct_str = f"{round(pct * 100)}%"
        payload = {
            "type": "context",
            "message": f"Context at {pct_str} — state saved to git. Opening new chat.",
            "goal": next_goal,
            "shown": False,
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)

        return True
    except Exception:
        return False


def _broadcast_session_end(developer: str, completed_goals: list, project_path: str, duration_seconds: int = 0):
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


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")
    _update_allowed_tools(transcript_path)

    # If daemon flagged a context checkpoint, handle it now that the exchange is done
    if _handle_pending_checkpoint(developer, transcript_path):
        _advance_launch_goal()
        return  # skip normal stop checkpoint — context checkpoint already did it

    from askr.session.checkpoint import create_checkpoint
    result = create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
    )

    completed_goals = result.get("completed_goals", [])
    duration_seconds = result.get("duration_seconds", 0)

    # Only send a card for meaningful stops — goals completed or session ran >5 min.
    # Suppresses noise from casual conversation turns and quick tests.
    if completed_goals or duration_seconds >= 300:
        _broadcast_session_end(developer, completed_goals, os.getcwd(), duration_seconds)

    _advance_launch_goal()


if __name__ == "__main__":
    main()
