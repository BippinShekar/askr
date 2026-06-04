#!/usr/bin/env python3
"""
Phase 2 - Session Lifecycle Daemon

Background process started by `askr launch`. Polls session stats every 30s.
When a threshold is crossed and it's safe, checkpoints and transitions:

  Trigger A (context >= 90%):
    checkpoint → kill claude → start new claude immediately

  Trigger B (quota >= 85%):
    checkpoint → kill claude → sleep until reset → start new claude

Started via: askr launch
Stopped via: askr launch --stop (kills by PID file)

Writes ~/.config/askr/daemon.pid while running.
Writes ~/.config/askr/launch_mode.json to signal SessionStart hook about
the active goal for the new session.
"""

import os
import sys

# Ensure the askr package root is on sys.path when run as a subprocess
_ASKR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ASKR_ROOT not in sys.path:
    sys.path.insert(0, _ASKR_ROOT)

import json
import time
import signal
import subprocess
from datetime import datetime, timezone

_PID_PATH        = os.path.expanduser("~/.config/askr/daemon.pid")
_STATS_PATH      = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH = os.path.expanduser("~/.config/askr/launch_mode.json")
_LOG_PATH        = os.path.expanduser("~/.config/askr/daemon.log")

POLL_INTERVAL    = 30   # seconds between stats checks
SAFE_RETRY_LIMIT = 3    # retries if not safe to pause
SAFE_RETRY_WAIT  = 60   # seconds to wait between retries


def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def _write_pid():
    os.makedirs(os.path.dirname(_PID_PATH), exist_ok=True)
    with open(_PID_PATH, "w") as f:
        f.write(str(os.getpid()))


def _clear_pid():
    try:
        os.remove(_PID_PATH)
    except Exception:
        pass


def _read_stats() -> dict:
    try:
        if not os.path.exists(_STATS_PATH):
            return {}
        mtime = os.path.getmtime(_STATS_PATH)
        # stale if not updated in 10 minutes (claude likely idle or stopped)
        if time.time() - mtime > 600:
            return {}
        with open(_STATS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _find_claude_pid() -> list:
    """Return list of PIDs for running claude processes."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "claude"],
            capture_output=True, text=True
        )
        return [int(p) for p in result.stdout.strip().splitlines() if p.strip().isdigit()]
    except Exception:
        return []


def _kill_claude():
    pids = _find_claude_pid()
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
            _log(f"sent SIGTERM to claude pid {pid}")
        except ProcessLookupError:
            pass
    if pids:
        time.sleep(2)
        # SIGKILL any that didn't exit
        for pid in _find_claude_pid():
            try:
                os.kill(pid, signal.SIGKILL)
                _log(f"sent SIGKILL to claude pid {pid}")
            except ProcessLookupError:
                pass


def _start_claude(project_path: str):
    try:
        subprocess.Popen(
            ["claude"],
            cwd=project_path,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log(f"started new claude session in {project_path}")
    except FileNotFoundError:
        _log("ERROR: 'claude' not found in PATH - cannot start new session")


def _wait_for_reset(reset_at_iso: str):
    try:
        reset_at = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        wait_seconds = (reset_at - now).total_seconds()
        if wait_seconds > 0:
            _log(f"quota reset at {reset_at.strftime('%H:%M UTC')} — sleeping {int(wait_seconds)}s")
            time.sleep(wait_seconds + 30)  # 30s buffer after reset
        else:
            _log("quota reset already passed, resuming immediately")
    except Exception as e:
        _log(f"could not parse reset time: {e} — waiting 5 minutes as fallback")
        time.sleep(300)


def _write_launch_mode(goal: str = ""):
    try:
        os.makedirs(os.path.dirname(_LAUNCH_MODE_PATH), exist_ok=True)
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump({"active": True, "goal": goal, "timestamp": datetime.now(timezone.utc).isoformat()}, f)
    except Exception:
        pass


def _get_next_goal() -> str:
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
        from askr.state.goals import load_today_goals, load_open_goals
        today = load_today_goals()
        if today:
            return today[0]
        open_goals = load_open_goals()
        if open_goals:
            return open_goals[0]
        return ""
    except Exception:
        return ""


def _execute_trigger(trigger: str, stats: dict, project_path: str):
    from askr.state.config import load_developer
    from askr.session.safe_pause import is_safe_to_pause
    from askr.session.checkpoint import create_checkpoint

    developer = load_developer()
    _log(f"trigger={trigger} — checking safe pause")

    for attempt in range(1, SAFE_RETRY_LIMIT + 1):
        safe, reason = is_safe_to_pause(project_path)
        if safe:
            break
        _log(f"not safe ({reason}) — retry {attempt}/{SAFE_RETRY_LIMIT} in {SAFE_RETRY_WAIT}s")
        if attempt < SAFE_RETRY_LIMIT:
            time.sleep(SAFE_RETRY_WAIT)
    else:
        _log(f"unsafe after {SAFE_RETRY_LIMIT} retries — skipping checkpoint this cycle")
        return

    _log("safe to pause — creating checkpoint")
    result = create_checkpoint(trigger_type=trigger, developer=developer)
    _log(f"checkpoint done: {result.get('trigger')} at {result.get('timestamp', '')[:19]}")

    next_goal = _get_next_goal()
    _write_launch_mode(next_goal)

    _kill_claude()

    if trigger == "quota":
        reset_at = stats.get("reset_at")
        if reset_at:
            _wait_for_reset(reset_at)
        else:
            _log("no reset_at in stats — waiting 5 minutes")
            time.sleep(300)

    _log("starting new claude session")
    _start_claude(project_path)


def run_daemon(project_path: str):
    _write_pid()
    _log(f"daemon started — project={project_path} poll={POLL_INTERVAL}s")

    def _on_term(sig, frame):
        _log("received SIGTERM — shutting down")
        _clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    try:
        while True:
            stats = _read_stats()
            if stats:
                ctx_pct       = stats.get("context_pct", 0)
                ctx_eta_turns = stats.get("context_eta_turns")
                q_eta_minutes = stats.get("quota_eta_minutes")

                # Trigger A: context at or above 90%
                context_hit = ctx_pct >= 0.90

                # Trigger B: quota window expiring within 30 minutes
                # (quota_eta_minutes is time until reset scaled by usage — when it
                # approaches 0 the window is nearly exhausted)
                quota_hit = q_eta_minutes is not None and q_eta_minutes <= 30

                if context_hit:
                    _log(f"Trigger A: context={ctx_pct:.1%} >= 90%")
                    _execute_trigger("context", stats, project_path)
                elif quota_hit:
                    _log(f"Trigger B: quota window expiring in {q_eta_minutes:.0f}min")
                    _execute_trigger("quota", stats, project_path)
                else:
                    eta_info = f"ctx_eta={ctx_eta_turns}t" if ctx_eta_turns else "ctx_eta=?"
                    q_info   = f"q_eta={q_eta_minutes:.0f}min" if q_eta_minutes else "q_eta=?"
                    _log(f"ok: ctx={ctx_pct:.1%} {eta_info} {q_info}")

            time.sleep(POLL_INTERVAL)
    finally:
        _clear_pid()


def stop_daemon() -> bool:
    """Kill the running daemon. Returns True if a process was found."""
    if not os.path.exists(_PID_PATH):
        return False
    try:
        with open(_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        _clear_pid()
        return True
    except (ProcessLookupError, ValueError):
        _clear_pid()
        return False


def daemon_is_running() -> bool:
    if not os.path.exists(_PID_PATH):
        return False
    try:
        with open(_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)  # signal 0 = existence check
        return True
    except (ProcessLookupError, ValueError, OSError):
        _clear_pid()
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_path")
    args = parser.parse_args()
    run_daemon(args.project_path)
