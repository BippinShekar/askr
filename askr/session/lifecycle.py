#!/usr/bin/env python3
"""
Session Lifecycle Daemon

Installed as a launchd service by `askr init`. Starts at login, runs silently.

Session liveness: detected from ~/.config/askr/session_stats.json mtime.
  active = updated within last 10 minutes (Claude session running)
  idle   = stale or missing (no session)

Trigger A — context >= 75%:
  Read from session_stats.json (accurate: parsed from JSONL token counts)
  safe_pause check → checkpoint → kill claude → start new claude immediately

Trigger B — quota >= 90%:
  Read from session_stats.json (accurate: from Anthropic's /api/oauth/usage endpoint)
  safe_pause check → checkpoint → kill claude → sleep until reset → start new claude
"""

import os
import sys
import subprocess as _bootstrap_sp

_ASKR_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ASKR_ROOT not in sys.path:
    sys.path.insert(0, _ASKR_ROOT)

# launchd starts with a minimal PATH that won't include user-installed CLIs like claude.
# Source the full shell PATH before anything else so shutil.which and Popen work correctly.
def _patch_path():
    try:
        result = _bootstrap_sp.run(
            ["zsh", "-l", "-c", "echo $PATH"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            os.environ["PATH"] = result.stdout.strip()
            return
    except Exception:
        pass
    # fallback: prepend the most common user-install locations
    extras = ":".join([
        os.path.expanduser("~/.local/bin"),
        "/opt/homebrew/bin",
        "/opt/homebrew/sbin",
        "/usr/local/bin",
    ])
    os.environ["PATH"] = extras + ":" + os.environ.get("PATH", "")

_patch_path()

import json
import time
import signal
import shutil
import subprocess
from datetime import datetime, timezone

_PID_PATH             = os.path.expanduser("~/.config/askr/daemon.pid")
_CAFFEINATE_PID_PATH  = os.path.expanduser("~/.config/askr/caffeinate.pid")
_CLAUDE_PID_PATH      = os.path.expanduser("~/.config/askr/claude_session.pid")
_STATS_PATH           = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH     = os.path.expanduser("~/.config/askr/launch_mode.json")
_NOTIFICATION_PATH    = os.path.expanduser("~/.config/askr/notification.json")
_LOG_PATH             = os.path.expanduser("~/.config/askr/daemon.log")

POLL_ACTIVE        = 30    # seconds when session is live
POLL_IDLE          = 60    # seconds when no session
SESSION_STALE_SECS = 600   # 10 min without stats update → session ended
SAFE_RETRY_LIMIT   = 3
SAFE_RETRY_WAIT    = 60
CONTEXT_TRIGGER    = 0.75  # fire when context reaches 75% — research shows degradation well before 90%
QUOTA_TRIGGER      = 90.0  # fire when 5h quota reaches 90% (real API %)
TRIGGER_COOLDOWN   = 300   # seconds to ignore further triggers after one fires


# ---------------------------------------------------------------------------
# Logging — stdout only; launchd plist captures stdout to daemon.log.
# Never write directly to the file here to avoid double-logging.
# ---------------------------------------------------------------------------

def _log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


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
        _log("caffeinate started")
        try:
            r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
            if "Battery Power" in r.stdout:
                _log("WARNING: on battery — lid close will sleep device regardless of caffeinate")
        except Exception:
            pass
    except FileNotFoundError:
        _log("WARNING: caffeinate not found")
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
        _log("caffeinate stopped")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Session liveness — based on stats file mtime
# ---------------------------------------------------------------------------

def _session_is_active() -> bool:
    try:
        return time.time() - os.path.getmtime(_STATS_PATH) < SESSION_STALE_SECS
    except Exception:
        return False


def _read_stats() -> dict:
    """
    Read session_stats.json. Returns {} if the file is missing or stale.
    Stats are written by post_tool_use.py after every tool execution.
    """
    try:
        if not _session_is_active():
            return {}
        with open(_STATS_PATH) as f:
            data = json.load(f)
        # Extra guard: reject stats whose updated_at is older than SESSION_STALE_SECS
        # (mtime and updated_at should agree, but belt-and-suspenders)
        ua = data.get("updated_at", "")
        if ua:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(ua)).total_seconds()
            if age > SESSION_STALE_SECS:
                return {}
        return data
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Claude process management
# ---------------------------------------------------------------------------

def _claude_cli_available() -> bool:
    return shutil.which("claude") is not None


def _write_claude_pid(pid: int):
    try:
        os.makedirs(os.path.dirname(_CLAUDE_PID_PATH), exist_ok=True)
        with open(_CLAUDE_PID_PATH, "w") as f:
            f.write(str(pid))
    except Exception:
        pass


def _read_claude_pid() -> int | None:
    try:
        with open(_CLAUDE_PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except Exception:
        return None


def _clear_claude_pid():
    try:
        os.remove(_CLAUDE_PID_PATH)
    except Exception:
        pass


def _kill_claude():
    """Kill only the tracked claude PID we launched. Never blindly kills by name."""
    pid = _read_claude_pid()
    if pid is None:
        _log("no tracked claude PID to kill — skipping")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        _log(f"sent SIGTERM to claude pid {pid}")
    except ProcessLookupError:
        pass
    time.sleep(2)
    try:
        os.kill(pid, 0)
        os.kill(pid, signal.SIGKILL)
        _log(f"sent SIGKILL to claude pid {pid}")
    except ProcessLookupError:
        pass
    _clear_claude_pid()


def _start_claude(project_path: str):
    if not _claude_cli_available():
        _log("ERROR: 'claude' not in PATH — cannot start new session")
        return
    try:
        proc = subprocess.Popen(
            ["claude"],
            cwd=project_path,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _write_claude_pid(proc.pid)
        _log(f"started new claude session in {project_path} (pid={proc.pid})")
    except FileNotFoundError:
        _log("ERROR: 'claude' not in PATH — cannot start new session")


def _wait_for_reset(reset_at_iso: str):
    """Sleep until the exact quota reset time from the API."""
    try:
        reset_at = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
        wait_secs = (reset_at - datetime.now(timezone.utc)).total_seconds()
        if wait_secs > 0:
            _log(f"quota resets at {reset_at.strftime('%H:%M UTC')} — sleeping {int(wait_secs)}s")
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


def _write_notification(trigger: str, goal: str = "", pct: float = 0.0, handover_ready: bool = False):
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        pct_str = f"{round(pct * 100)}%" if trigger == "context" else f"{round(pct)}%"
        if trigger == "context":
            msg = f"Context at {pct_str} — state saved to git. Opening new chat."
        else:
            msg = f"Quota at {pct_str} — state saved to git. Waiting for reset, then resuming."
        payload = {
            "type": trigger,
            "message": msg,
            "goal": goal,
            "handover_ready": handover_ready,
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

    if not _claude_cli_available():
        _log("WARN: 'claude' not in PATH — skipping trigger (would leave user with nothing)")
        return

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
    pct = stats.get("context_pct", 0.0) if trigger == "context" else stats.get("quota_pct", 0.0)
    handover_path = result.get("handover_path", "")
    handover_has_content = bool(handover_path and os.path.exists(handover_path) and
                                os.path.getsize(handover_path) > 200)
    _write_notification(trigger, next_goal, pct, handover_has_content)
    _kill_claude()

    if trigger == "quota":
        reset_at = stats.get("quota_reset_at")
        if reset_at:
            _wait_for_reset(reset_at)
        else:
            time.sleep(300)

    _log("starting new claude session")
    _start_claude(project_path)


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------

def run_daemon():
    # Single-instance guard — exit immediately if another instance is already running
    if os.path.exists(_PID_PATH):
        try:
            with open(_PID_PATH) as f:
                existing_pid = int(f.read().strip())
            if existing_pid != os.getpid():
                os.kill(existing_pid, 0)  # raises if process is dead
                _log(f"another instance already running (pid={existing_pid}) — exiting")
                sys.exit(0)
        except (ProcessLookupError, ValueError, OSError):
            pass  # stale PID file — safe to overwrite

    _write_pid()
    _log("daemon started")

    was_active = False
    last_trigger_at = 0.0  # epoch seconds — prevents re-firing on the same session

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
                    ctx_pct    = stats.get("context_pct", 0)
                    ctx_label  = stats.get("context_label", "ok")
                    quota_pct  = stats.get("quota_pct")    # real % from /api/oauth/usage
                    reset_at   = stats.get("quota_reset_at", "")

                    in_cooldown = (time.time() - last_trigger_at) < TRIGGER_COOLDOWN

                    if in_cooldown:
                        remaining = int(TRIGGER_COOLDOWN - (time.time() - last_trigger_at))
                        _log(f"cooldown: {remaining}s remaining — ctx={ctx_pct:.1%} quota={quota_pct or 0:.1f}%")
                    elif ctx_pct >= CONTEXT_TRIGGER:
                        _log(f"Trigger A: context={ctx_pct:.1%} [{ctx_label}]")
                        _execute_trigger("context", stats, project_path)
                        last_trigger_at = time.time()
                    elif quota_pct is not None and quota_pct >= QUOTA_TRIGGER:
                        _log(f"Trigger B: quota={quota_pct:.1f}% (real API)")
                        _execute_trigger("quota", stats, project_path)
                        last_trigger_at = time.time()
                    else:
                        q_str = f"quota={quota_pct:.1f}%" if quota_pct is not None else "quota=?"
                        _log(f"ok: ctx={ctx_pct:.1%} [{ctx_label}] {q_str}")

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
