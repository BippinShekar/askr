#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Emergency fallback — fires when Claude is about to auto-compact the context.
The 65% daemon trigger should prevent this from ever firing in normal operation.
When it does fire (single-turn extended-thinking jump, or quota exhaustion
causing Claude Code to auto-compact), we checkpoint and kill the session.
The Stop hook then handles restart vs wait-for-reset based on quota state.

PreCompact cannot block compaction via its return value — killing the process
is the only way to guarantee a fresh session instead of a compressed one.
"""

import sys
import os
import json
import signal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer

_CLAUDE_PID_PATH    = os.path.expanduser("~/.config/askr/claude_session.pid")
_CHECKPOINT_PENDING = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
QUOTA_HIGH          = 85.0  # treat as quota-exhausted if above this


def _read_claude_pid():
    """Return Claude's PID from the tracked file, or fall back to pgrep by cwd."""
    try:
        with open(_CLAUDE_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        pass
    # PID file missing or stale — search by project cwd (handles manually-opened sessions)
    try:
        import subprocess
        result = subprocess.run(
            ["pgrep", "-x", "claude"],
            capture_output=True, text=True, timeout=5,
        )
        project_path = os.getcwd()
        for pid_str in result.stdout.strip().splitlines():
            try:
                pid = int(pid_str)
                lsof = subprocess.run(
                    ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-F", "n"],
                    capture_output=True, text=True, timeout=3,
                )
                for line in lsof.stdout.splitlines():
                    if line.startswith("n") and line[1:] == project_path:
                        return pid
            except Exception:
                continue
    except Exception:
        pass
    return None


def _quota_pct() -> float | None:
    try:
        from askr.session.monitor import stats_path_for_project, find_project_root
        stats_path = stats_path_for_project(find_project_root())
        with open(stats_path) as f:
            return json.load(f).get("quota_pct")
    except Exception:
        return None


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()

    from askr.session.checkpoint import create_checkpoint
    create_checkpoint(
        trigger_type="emergency",
        developer=developer,
        transcript_path=payload.get("transcript_path", ""),
    )

    pid = _read_claude_pid()
    if not pid:
        # No tracked PID — can't kill, at least state is saved
        print(json.dumps({
            "custom_instructions": "Askr has checkpointed state to git. A new session will resume from the handover."
        }))
        return

    # If quota is high, mark checkpoint_pending as quota-type so the Stop hook
    # waits for reset instead of immediately opening a new session.
    quota = _quota_pct()
    if quota is not None and quota >= QUOTA_HIGH:
        try:
            with open(_CHECKPOINT_PENDING) as f:
                pending = json.load(f)
        except Exception:
            pending = {}
        pending["trigger"] = "quota"
        os.makedirs(os.path.dirname(_CHECKPOINT_PENDING), exist_ok=True)
        with open(_CHECKPOINT_PENDING, "w") as f:
            json.dump(pending, f)

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


if __name__ == "__main__":
    main()
