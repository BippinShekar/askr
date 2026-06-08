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


def _broadcast_session_end(developer: str, completed_goals: list, project_path: str):
    try:
        from askr.clients.discord import send_message
        lines = [f"**[askr] Session ended** — {developer}"]

        if completed_goals:
            lines.append("**Goals completed:**")
            lines.extend(f"✓ {g}" for g in completed_goals)

        try:
            # Files changed
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "--name-only"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            files = [
                f for f in result.stdout.strip().splitlines()
                if not f.startswith("askr_state/")
            ]
            if files:
                lines.append("**Files changed:**")
                lines.extend(f"  {f}" for f in files[:10])
                if len(files) > 10:
                    lines.append(f"  …and {len(files) - 10} more")

            # What changed and why — last commit message
            msg_result = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            commit_msg = msg_result.stdout.strip()
            if commit_msg and not commit_msg.startswith("askr:"):
                lines.append(f"**Last commit:** {commit_msg}")

            # One-line diff stat
            stat_result = subprocess.run(
                ["git", "diff", "HEAD~1", "--stat", "--no-color"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            stat_lines = [l for l in stat_result.stdout.strip().splitlines()
                         if "changed" in l]
            if stat_lines:
                lines.append(f"**{stat_lines[-1].strip()}**")
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

    # If daemon flagged a context checkpoint, handle it now that the exchange is done
    if _handle_pending_checkpoint(developer, transcript_path):
        _advance_launch_goal()
        return  # skip normal stop checkpoint — context checkpoint already did it

    from askr.session.checkpoint import create_checkpoint
    from askr.state.config import load_project_path
    result = create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
    )

    completed_goals = result.get("completed_goals", [])
    _broadcast_session_end(developer, completed_goals, load_project_path())
    _advance_launch_goal()


if __name__ == "__main__":
    main()
