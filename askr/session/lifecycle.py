#!/usr/bin/env python3
"""
Phase 2 - Session Lifecycle Daemon

Installed as a launchd service by `askr init`. Starts at login, runs silently.
No manual start needed — it is always on.

Session liveness: detected from ~/.config/askr/session_stats.json mtime.
  active  = updated within last 10 minutes (Claude session running)
  idle    = stale or missing (no session)

When session goes active:
  → start caffeinate -i  (prevents system sleep, allows display to dim)
  → poll every 30s for threshold breaches

When session goes idle:
  → stop caffeinate  (device can sleep normally)
  → poll every 60s

Trigger A (context >= 90%):
  safe_pause check → checkpoint → kill claude → start new claude immediately

Trigger B (quota window <= 30 min remaining):
  safe_pause check → checkpoint → kill claude → sleep until reset → start new claude

Battery note: caffeinate -i cannot prevent sleep when lid is closed on battery.
Plugging in is required for reliable overnight runs.
"""

import os
import sys

_ASKR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ASKR_ROOT not in sys.path:
    sys.path.insert(0, _ASKR_ROOT)

import json
import time
import signal
import subprocess
from datetime import datetime, timezone

_PID_PATH             = os.path.expanduser("~/.config/askr/daemon.pid")
_CAFFEINATE_PID_PATH  = os.path.expanduser("~/.config/askr/caffeinate.pid")
_STATS_PATH           = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH     = os.path.expanduser("~/.config/askr/launch_mode.json")
_NOTIFICATION_PATH    = os.path.expanduser("~/.config/askr/notification.json")
_LOG_PATH             = os.path.expanduser("~/.config/askr/daemon.log")

POLL_ACTIVE        = 30   # seconds when session is live
POLL_IDLE          = 60   # seconds when no session
SESSION_STALE_SECS = 600  # 10 min without update → session ended
SAFE_RETRY_LIMIT   = 3
SAFE_RETRY_WAIT    = 60


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# PID management
# ---------------------------------------------------------------------------

def _write_pid():
    os.makedirs(os.path.dirname(_PID_PATH), exist_ok=True)
    with open(_PID_PATH, "w") as f:
        f.write(str(os.getpid()))


def _clear_pid():
    try:
        os.remove(_PID_PATH)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Caffeinate
# ---------------------------------------------------------------------------

def _caffeinate_running() -> bool:
    try:
        if not os.path.exists(_CAFFEINATE_PID_PATH):
            return False
        with open(_CAFFEINATE_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        try:
            os.remove(_CAFFEINATE_PID_PATH)
        except Exception:
            pass
        return False


def _start_caffeinate():
    if _caffeinate_running():
        return
    try:
        proc = subprocess.Popen(
            ["caffeinate", "-i"],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.makedirs(os.path.dirname(_CAFFEINATE_PID_PATH), exist_ok=True)
        with open(_CAFFEINATE_PID_PATH, "w") as f:
            f.write(str(proc.pid))
        _log("caffeinate -i started — system sleep prevented, display can dim")

        # Warn if on battery
        try:
            r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
            if "Battery Power" in r.stdout:
                _log("WARNING: on battery — close lid will sleep device regardless of caffeinate. Plug in for overnight runs.")
        except Exception:
            pass

    except FileNotFoundError:
        _log("WARNING: caffeinate not found — device may sleep during session")
    except Exception as e:
        _log(f"caffeinate start failed: {e}")


def _stop_caffeinate():
    if not _caffeinate_running():
        return
    try:
        with open(_CAFFEINATE_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        try:
            os.remove(_CAFFEINATE_PID_PATH)
        except Exception:
            pass
        _log("caffeinate stopped — device can sleep normally")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session liveness
# ---------------------------------------------------------------------------

def _session_is_active() -> bool:
    try:
        return time.time() - os.path.getmtime(_STATS_PATH) < SESSION_STALE_SECS
    except Exception:
        return False


def _read_stats() -> dict:
    try:
        if not _session_is_active():
            return {}
        with open(_STATS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Claude process
# ---------------------------------------------------------------------------

def _find_claude_pids() -> list:
    try:
        # -x = exact process name match; avoids killing Cursor extension hosts
        # whose cmdlines contain ".cursor/extensions/anthropic.claude-code-..."
        r = subprocess.run(["pgrep", "-x", "claude"], capture_output=True, text=True)
        return [int(p) for p in r.stdout.strip().splitlines() if p.strip().isdigit()]
    except Exception:
        return []


def _kill_claude():
    for pid in _find_claude_pids():
        try:
            os.kill(pid, signal.SIGTERM)
            _log(f"sent SIGTERM to claude pid {pid}")
        except ProcessLookupError:
            pass
    if _find_claude_pids():
        time.sleep(2)
        for pid in _find_claude_pids():
            try:
                os.kill(pid, signal.SIGKILL)
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
        _log("ERROR: 'claude' not found in PATH — cannot start new session")


def _wait_for_reset(reset_at_iso: str):
    try:
        reset_at = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
        wait_secs = (reset_at - datetime.now(timezone.utc)).total_seconds()
        if wait_secs > 0:
            _log(f"quota reset at {reset_at.strftime('%H:%M UTC')} — sleeping {int(wait_secs)}s")
            time.sleep(wait_secs + 30)
        else:
            _log("quota reset already passed — resuming immediately")
    except Exception:
        _log("could not parse reset time — waiting 5 min as fallback")
        time.sleep(300)


def _get_next_goal() -> str:
    try:
        from askr.state.goals import load_today_goals, load_open_goals
        today = load_today_goals()
        if today:
            return today[0]
        return (load_open_goals() or [""])[0]
    except Exception:
        return ""


def _write_launch_mode(goal: str = ""):
    try:
        os.makedirs(os.path.dirname(_LAUNCH_MODE_PATH), exist_ok=True)
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump({
                "active": True,
                "goal": goal,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
    except Exception:
        pass


def _write_notification(trigger: str, goal: str = ""):
    """
    Write a notification for the IDE extension to surface as a VS Code alert.
    The extension polls this file and shows showWarningMessage() when seen.
    """
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        if trigger == "context":
            msg = "Context at 90% — state saved to git. Open a new chat to continue."
        else:
            msg = "Quota window low — state saved to git. Waiting for reset, then resuming."
        payload = {
            "type": trigger,
            "message": msg,
            "goal": goal,
            "shown": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Trigger execution
# ---------------------------------------------------------------------------

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
        _log(f"unsafe after {SAFE_RETRY_LIMIT} retries — skipping this cycle")
        return

    _log("safe to pause — creating checkpoint")
    result = create_checkpoint(trigger_type=trigger, developer=developer)
    _log(f"checkpoint: {result.get('trigger')} at {result.get('timestamp', '')[:19]}")

    next_goal = _get_next_goal()
    _write_launch_mode(next_goal)
    _write_notification(trigger, next_goal)
    _kill_claude()

    if trigger == "quota":
        reset_at = stats.get("reset_at")
        _wait_for_reset(reset_at) if reset_at else time.sleep(300)

    _log("starting new claude session")
    _start_claude(project_path)


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------

def run_daemon():
    """
    Always-on daemon. Installed via launchd; starts at login.
    No project_path argument — reads from ~/.config/askr/config.json.
    """
    _write_pid()
    _log("daemon started (always-on mode)")

    was_active = False

    def _on_term(sig, frame):
        _log("received SIGTERM — stopping")
        _stop_caffeinate()
        _clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    try:
        while True:
            from askr.state.config import load_project_path
            project_path = load_project_path()

            active = _session_is_active()

            if active and not was_active:
                _log(f"session active — project={project_path}")
                _start_caffeinate()
            elif not active and was_active:
                _log("session ended or went idle")
                _stop_caffeinate()

            was_active = active

            if active:
                stats = _read_stats()
                if stats:
                    ctx_pct       = stats.get("context_pct", 0)
                    ctx_label     = stats.get("context_label", "ok")
                    q_eta_minutes = stats.get("quota_eta_minutes")

                    if ctx_pct >= 0.90:
                        _log(f"Trigger A: context={ctx_pct:.1%} [{ctx_label}]")
                        _execute_trigger("context", stats, project_path)
                    elif q_eta_minutes is not None and q_eta_minutes <= 30:
                        _log(f"Trigger B: quota window expiring in {q_eta_minutes:.0f}min")
                        _execute_trigger("quota", stats, project_path)
                    else:
                        q_info = f"q_eta={q_eta_minutes:.0f}min" if q_eta_minutes else "q_eta=?"
                        _log(f"ok: ctx={ctx_pct:.1%} [{ctx_label}] {q_info}")

                time.sleep(POLL_ACTIVE)
            else:
                time.sleep(POLL_IDLE)

    finally:
        _stop_caffeinate()
        _clear_pid()


# ---------------------------------------------------------------------------
# Control helpers (used by CLI)
# ---------------------------------------------------------------------------

def stop_daemon() -> bool:
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
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, ValueError, OSError):
        _clear_pid()
        return False


if __name__ == "__main__":
    run_daemon()
