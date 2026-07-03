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
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer

_CHECKPOINT_PENDING   = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
_LAST_EMERGENCY_SPEAK = os.path.expanduser("~/.config/askr/pre_compact_last_speak.json")
QUOTA_HIGH            = 85.0  # treat as quota-exhausted if above this
SPEAK_COOLDOWN_SECS   = 180   # don't re-announce more than once per 3 min


def _should_speak_emergency() -> bool:
    """PreCompact has no natural dedup — if a session sits at/near 100% context
    and the user keeps sending messages into that same (already full) window
    instead of switching to the companion session askr already opened, native
    compaction can trigger again on every subsequent message, re-firing this
    hook every time. The checkpoint+kill below still has to run every time
    (that part is genuinely needed each time compaction is imminent), but the
    voice announcement doesn't need to repeat the identical line every few
    seconds — cap it to once per SPEAK_COOLDOWN_SECS."""
    try:
        if os.path.exists(_LAST_EMERGENCY_SPEAK):
            with open(_LAST_EMERGENCY_SPEAK) as f:
                last = datetime.fromisoformat(json.load(f).get("at", ""))
            if (datetime.now(timezone.utc) - last).total_seconds() < SPEAK_COOLDOWN_SECS:
                return False
    except Exception:
        pass
    return True


def _mark_emergency_spoken():
    try:
        os.makedirs(os.path.dirname(_LAST_EMERGENCY_SPEAK), exist_ok=True)
        with open(_LAST_EMERGENCY_SPEAK, "w") as f:
            json.dump({"at": datetime.now(timezone.utc).isoformat()}, f)
    except Exception:
        pass


def _speak(message: str):
    try:
        from askr.clients.voice import announce
        announce(message)
    except Exception:
        pass


def _latest_stats() -> dict:
    """Most recent stats file for this project (quota is per-account, context is per-session)."""
    try:
        from askr.session.monitor import find_project_root, find_project_stats_files
        project_path = find_project_root()
        for path in sorted(find_project_stats_files(project_path), key=os.path.getmtime, reverse=True):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                continue
    except Exception:
        pass
    return {}


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
    # for Stop to fire cleanly after SIGTERM. Rate-limited: if this window is
    # sitting at/near 100% context and messages keep coming, compaction can
    # trigger again on every message — the checkpoint+kill must still run each
    # time, but the announcement shouldn't repeat every few seconds.
    if _should_speak_emergency():
        _speak("Context full — this session can't continue. A companion session "
               "should already be open; switch to it. Checkpointing this one now.")
        _mark_emergency_spoken()

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
    #
    # Always write a complete, fresh payload here — never merge onto whatever's
    # already on disk. This used to patch just "trigger" onto the existing file
    # (or {} if unreadable), leaving quota_pct/context_pct/timestamp as whatever
    # ancient values were last written by lifecycle.py's _write_checkpoint_pending()
    # — which was removed entirely in 65e543b. Any pre-existing file is from a
    # different (possibly days-old) event; carrying its stale numbers forward is
    # exactly what caused the Stop hook to announce a wildly wrong quota% on an
    # otherwise healthy session.
    stats = _latest_stats()
    quota = stats.get("quota_pct")
    if quota is not None and quota >= QUOTA_HIGH:
        os.makedirs(os.path.dirname(_CHECKPOINT_PENDING), exist_ok=True)
        with open(_CHECKPOINT_PENDING, "w") as f:
            json.dump({
                "trigger": "quota",
                "quota_pct": quota,
                "context_pct": stats.get("context_pct", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)

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
