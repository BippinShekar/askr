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

_CHECKPOINT_PENDING = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
QUOTA_HIGH          = 85.0  # treat as quota-exhausted if above this


def _speak(message: str):
    try:
        from askr.clients.voice import speak
        speak(message)
    except Exception:
        pass


def _quota_pct() -> float | None:
    """Read quota from any recent stats file for this project (quota is per-account)."""
    try:
        from askr.session.monitor import find_project_root, find_project_stats_files
        project_path = find_project_root()
        for path in sorted(find_project_stats_files(project_path), key=os.path.getmtime, reverse=True):
            try:
                with open(path) as f:
                    quota = json.load(f).get("quota_pct")
                if quota is not None:
                    return quota
            except Exception:
                continue
    except Exception:
        pass
    return None


def _find_session_pid(transcript_path: str) -> int | None:
    """
    Find the PID of the Claude process that owns this specific session transcript.
    Uses lsof to find which process has the JSONL file open — this is precise
    and correct for multi-session scenarios because each session has a unique file.
    Falls back to pgrep+cwd match if lsof returns nothing (e.g. file not yet flushed).
    """
    import subprocess
    # Primary: find by open file handle — exact match for this session
    if transcript_path and os.path.exists(transcript_path):
        try:
            result = subprocess.run(
                ["lsof", "-t", transcript_path],
                capture_output=True, text=True, timeout=5,
            )
            for pid_str in result.stdout.strip().splitlines():
                try:
                    pid = int(pid_str)
                    os.kill(pid, 0)
                    return pid
                except Exception:
                    continue
        except Exception:
            pass

    # Fallback: first Claude process whose cwd matches this project
    try:
        project_path = os.getcwd()
        result = subprocess.run(
            ["pgrep", "-x", "claude"],
            capture_output=True, text=True, timeout=5,
        )
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


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")

    # Speak first, before the (potentially slow) checkpoint call — this is the
    # only voice announcement for a mid-turn kill, since PreCompact can't wait
    # for Stop to fire cleanly after SIGTERM.
    _speak("Context critical. Claude is compacting — restarting your session now.")

    from askr.session.checkpoint import create_checkpoint
    create_checkpoint(
        trigger_type="emergency",
        developer=developer,
        transcript_path=transcript_path,
    )

    # Kill only THIS session — PreCompact fires inside one session; other sessions
    # each have their own PreCompact hook and handle themselves independently.
    pid = _find_session_pid(transcript_path)
    if not pid:
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

    # Delete own stats file before dying — prevents the daemon from re-triggering
    # on a dead session's stale high ctx% after the cooldown expires.
    if transcript_path:
        try:
            from askr.session.monitor import stats_path_for_session, find_project_root
            session_id = os.path.basename(transcript_path).replace(".jsonl", "")
            sp = stats_path_for_session(find_project_root(), session_id)
            if os.path.exists(sp):
                os.remove(sp)
        except Exception:
            pass

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


if __name__ == "__main__":
    main()
