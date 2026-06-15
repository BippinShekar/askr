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
import shlex
import shutil
import subprocess
from datetime import datetime, timezone

_PID_PATH              = os.path.expanduser("~/.config/askr/daemon.pid")
_CAFFEINATE_PID_PATH   = os.path.expanduser("~/.config/askr/caffeinate.pid")
_CLAUDE_PID_PATH       = os.path.expanduser("~/.config/askr/claude_session.pid")
_STATS_PATH            = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH      = os.path.expanduser("~/.config/askr/launch_mode.json")
_NOTIFICATION_PATH     = os.path.expanduser("~/.config/askr/notification.json")
_CHECKPOINT_PENDING    = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
_LOG_PATH              = os.path.expanduser("~/.config/askr/daemon.log")

# ---------------------------------------------------------------------------
# Source self-watch — detect when askr code changes and restart cleanly.
# launchd KeepAlive:true means a clean exit triggers an automatic restart,
# so sys.exit(0) here is equivalent to "reload with new code".
# ---------------------------------------------------------------------------

_ASKR_SRC_DIR = os.path.join(_ASKR_ROOT, "askr")
_EXTENSION_PATHS = [
    os.path.expanduser("~/.cursor/extensions/askr.askr-status-1.0.0/extension.js"),
    os.path.expanduser("~/.vscode/extensions/askr.askr-status-1.0.0/extension.js"),
]


def _max_source_mtime() -> float:
    try:
        return max(
            os.path.getmtime(os.path.join(root, f))
            for root, _, files in os.walk(_ASKR_SRC_DIR)
            for f in files
            if f.endswith(".py") and "__pycache__" not in root
        )
    except Exception:
        return 0.0


def _extension_mtime() -> float:
    try:
        return max(
            (os.path.getmtime(p) for p in _EXTENSION_PATHS if os.path.exists(p)),
            default=0.0,
        )
    except Exception:
        return 0.0


_STARTUP_SOURCE_MTIME    = _max_source_mtime()
_STARTUP_EXTENSION_MTIME = _extension_mtime()

POLL_ACTIVE        = 30    # seconds when session is live
POLL_IDLE          = 60    # seconds when no session
SESSION_STALE_SECS = 600   # 10 min without stats update → session ended
SAFE_RETRY_LIMIT   = 3
SAFE_RETRY_WAIT    = 60
CONTEXT_TRIGGER    = 0.65  # fire at 65% — gives enough runway before auto-compact while reducing spurious kills on extended-thinking sessions
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

_STATS_DIR = os.path.expanduser("~/.config/askr/stats")


def _session_is_active() -> bool:
    """True if any per-project stats file was updated within the stale window."""
    try:
        if not os.path.isdir(_STATS_DIR):
            return False
        now = time.time()
        return any(
            now - os.path.getmtime(os.path.join(_STATS_DIR, f)) < SESSION_STALE_SECS
            for f in os.listdir(_STATS_DIR) if f.endswith(".json")
        )
    except Exception:
        return False


def _read_stats() -> dict:
    """
    Return stats from the most recently modified per-project stats file.
    Each project writes to its own file so concurrent sessions never collide.
    """
    try:
        if not os.path.isdir(_STATS_DIR):
            return {}
        now = time.time()
        candidates = [
            (os.path.getmtime(os.path.join(_STATS_DIR, f)), os.path.join(_STATS_DIR, f))
            for f in os.listdir(_STATS_DIR)
            if f.endswith(".json") and now - os.path.getmtime(os.path.join(_STATS_DIR, f)) < SESSION_STALE_SECS
        ]
        if not candidates:
            return {}
        _, active_path = max(candidates)
        with open(active_path) as f:
            data = json.load(f)
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


def _find_claude_pid_by_project(project_path: str) -> int | None:
    """Find a running 'claude' process whose cwd matches project_path."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "claude"],
            capture_output=True, text=True,
        )
        for pid_str in result.stdout.strip().splitlines():
            try:
                pid = int(pid_str)
                lsof_result = subprocess.run(
                    ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-F", "n"],
                    capture_output=True, text=True, timeout=3,
                )
                for line in lsof_result.stdout.splitlines():
                    if line.startswith("n") and line[1:] == project_path:
                        return pid
            except Exception:
                continue
    except Exception:
        pass
    return None


def _kill_claude(project_path: str = ""):
    """Kill the tracked claude PID, or fall back to finding it by project cwd."""
    pid = _read_claude_pid()
    if pid is None and project_path:
        pid = _find_claude_pid_by_project(project_path)
        if pid:
            _log(f"no tracked PID — found claude pid {pid} by cwd")
    if pid is None:
        _log("no tracked claude PID to kill — skipping")
        return
    try:
        os.kill(pid, signal.SIGTERM)
        _log(f"sent SIGTERM to claude pid {pid}")
    except ProcessLookupError:
        _clear_claude_pid()
        return
    # Give Claude 15s to run Stop hook and exit gracefully.
    # 2s was too short for extended-thinking sessions mid-API-call.
    for _ in range(15):
        time.sleep(1)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            _log(f"claude pid {pid} exited cleanly after SIGTERM")
            _clear_claude_pid()
            return
    try:
        os.kill(pid, signal.SIGKILL)
        _log(f"sent SIGKILL to claude pid {pid} (still alive after 15s)")
    except ProcessLookupError:
        pass
    _clear_claude_pid()


def _load_allowed_tools(project_path: str) -> list:
    """Read allowedTools from the project's .claude/settings.json."""
    try:
        settings_path = os.path.join(project_path, ".claude", "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                return json.load(f).get("allowedTools", [])
    except Exception:
        pass
    return []


def _start_claude(project_path: str, initial_prompt: str = "") -> bool:
    if not _claude_cli_available():
        _log("ERROR: 'claude' not in PATH — cannot start new session")
        return False

    # Refuse to open a new session if Claude is already running for this project
    existing = _find_claude_pid_by_project(project_path)
    if existing:
        _log(f"Claude pid {existing} already running for {project_path} — skipping launch to prevent double-session")
        return False

    claude_bin = shutil.which("claude") or "claude"

    allowed_tools = _load_allowed_tools(project_path)
    tools_flag = f" --allowedTools {','.join(allowed_tools)}" if allowed_tools else ""

    goal_part = f" (High-level goal for context: {initial_prompt}.)" if initial_prompt else ""
    prompt_arg = f"Read the handover file and execute the Next Action listed there immediately.{goal_part} The handover's Next Action takes priority over everything else. Work autonomously."

    display_goal = initial_prompt or "autonomous session"

    # Signal the VS Code/Cursor extension to open an integrated terminal.
    notification_written = False
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump({
                "type": "goal_launch",
                "goal": display_goal,
                "prompt": prompt_arg,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "message": f"Starting autonomous session — {display_goal}",
                "shown": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
        notification_written = True
        _log("wrote goal_launch notification — extension will open IDE terminal if active")
    except Exception as e:
        _log(f"notification write failed: {e}")

    # Spawn a background process: after 6 seconds check if the extension marked the
    # notification shown. If not (extension not loaded/reloaded), open Terminal.app.
    # This way a reloaded extension gets sole control; an unloaded one gracefully
    # falls back to Terminal.app without blocking the caller.
    safe_prompt = prompt_arg.replace("'", "").replace('"', "").replace("\\", "")
    notif_path  = _NOTIFICATION_PATH
    fallback_script = (
        f"import time, json, os, subprocess\n"
        f"time.sleep(6)\n"
        f"try:\n"
        f"    with open({repr(notif_path)}) as _f:\n"
        f"        _d = json.load(_f)\n"
        f"    if _d.get('shown'): exit(0)\n"
        f"except Exception: pass\n"
        f"# Step 1: open Terminal.app and start claude\n"
        f"_start_cmd = 'cd {project_path} && {claude_bin}{tools_flag}'\n"
        f"_open_script = 'tell application \"Terminal\"\\n  do script \"' + _start_cmd + '\"\\n  activate\\nend tell'\n"
        f"subprocess.run(['osascript', '-e', _open_script], timeout=5, "
        f"stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
        f"# Step 2: wait for claude TUI to load then type and submit the prompt\n"
        f"time.sleep(10)\n"
        f"_type_script = 'tell application \"Terminal\"\\n  tell front window\\n"
        f"    keystroke {repr(safe_prompt)}\\n    key code 36\\n  end tell\\nend tell'\n"
        f"subprocess.run(['osascript', '-e', _type_script], timeout=5, "
        f"stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
    )
    try:
        subprocess.Popen(
            [sys.executable, "-c", fallback_script],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log("fallback watcher spawned — Terminal.app fires in 6s if extension doesn't handle it")
    except Exception as e:
        _log(f"fallback watcher spawn failed: {e}")
    return True


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


def _write_checkpoint_pending(stats: dict):
    """
    Signal the Stop hook to checkpoint after the current exchange completes.
    The daemon never cuts in mid-exchange for context triggers — it just sets this flag.
    """
    try:
        os.makedirs(os.path.dirname(_CHECKPOINT_PENDING), exist_ok=True)
        with open(_CHECKPOINT_PENDING, "w") as f:
            json.dump({
                "trigger": "context",
                "context_pct": stats.get("context_pct", 0),
                "quota_pct": stats.get("quota_pct"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
    except Exception:
        pass


def _clear_checkpoint_pending():
    try:
        os.remove(_CHECKPOINT_PENDING)
    except Exception:
        pass


def _infer_direction(project_path: str = "") -> dict:
    """
    Infer what the next autonomous session should work on from deterministic signals.

    Signal priority (highest confidence first):
      1. Uncommitted files  — work was interrupted here (confidence 0.95)
      2. blockers.md        — something is explicitly stuck (confidence 0.90)
      3. git log momentum   — most-touched module in last 10 commits (confidence 0.72)
      4. Nothing            — no signal found (confidence 0.35)

    Returns {direction, confidence, signal_source, details}
    Never raises — all errors produce the low-confidence fallback.
    """
    cwd = project_path or os.getcwd()

    # Signal 1: uncommitted files
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10, cwd=cwd,
        )
        # Do NOT strip() stdout before splitlines — porcelain format is XY<SP>path,
        # and stripping the full output eats the leading space on the first line,
        # shifting l[3:] off by one for that entry.
        lines = [l for l in result.stdout.splitlines() if len(l) > 3]
        # Filter out askr_state/ noise — those are always modified by the stop hook
        dirty = [l[3:] for l in lines if not l[3:].startswith("askr_state/")]
        if dirty:
            file_list = ", ".join(dirty[:4]) + ("..." if len(dirty) > 4 else "")
            return {
                "direction": f"resume uncommitted work on: {file_list}",
                "confidence": 0.95,
                "signal_source": "uncommitted_files",
                "details": dirty,
            }
    except Exception:
        pass

    # Signal 2: blockers.md non-empty
    try:
        from askr.state.config import get_state_dir
        blockers_path = os.path.join(get_state_dir(), "blockers.md")
        if os.path.exists(blockers_path):
            content = open(blockers_path).read().strip()
            # Strip header/metadata lines — look for actual blocker entries
            _skip = {"none noted", "[none]", "none"}
            entries = [
                l.strip() for l in content.splitlines()
                if l.strip()
                and not l.startswith("#")
                and not l.lower().startswith("last updated")
                and l.strip().lower() not in _skip
            ]
            if entries:
                return {
                    "direction": f"resolve blocker: {entries[0][:120]}",
                    "confidence": 0.90,
                    "signal_source": "blockers_md",
                    "details": entries,
                }
    except Exception:
        pass

    # Signal 3: git log momentum — most-touched top-level module in last 10 commits
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--name-only", "-10"],
            capture_output=True, text=True, timeout=10, cwd=cwd,
        )
        from collections import Counter
        modules: Counter = Counter()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line[0] in "0123456789abcdef" or line.startswith("askr_state"):
                continue
            # Top-level module = first path component
            module = line.split("/")[0]
            if module:
                modules[module] += 1
        if modules:
            top_module, count = modules.most_common(1)[0]
            confidence = min(0.72, 0.50 + count * 0.04)  # scales with commit density
            return {
                "direction": f"continue work in {top_module}/ ({count} of last 10 commits)",
                "confidence": round(confidence, 2),
                "signal_source": "git_momentum",
                "details": dict(modules.most_common(5)),
            }
    except Exception:
        pass

    return {
        "direction": "",
        "confidence": 0.35,
        "signal_source": "none",
        "details": [],
    }


def _read_session_arc(developer: str, n: int = 5) -> str:
    """
    Read the last n sessions from git history of handover_<dev>.json.
    Uses 'git show <hash>:path' to get the full JSON at each commit — avoids
    the diff-interleaving problem of trying to parse +/- lines from git log -p.

    Synthesises a one-sentence arc via Haiku as a secondary direction signal.
    Returns empty string on any failure — never blocks session start.

    Quality note: arc accuracy depends on handover quality. Only called when
    primary signals (uncommitted files, blockers) are absent.
    """
    try:
        import json as _json
        from askr.state.config import get_state_dir
        state_dir = get_state_dir()
        rel_path = os.path.relpath(
            os.path.join(state_dir, f"handover_{developer}.json"),
            os.getcwd(),
        )

        # Get commit hashes that touched the handover file
        log_result = subprocess.run(
            ["git", "log", "--format=%H", "-" + str(n), "--", rel_path],
            capture_output=True, text=True, timeout=10, cwd=os.getcwd(),
        )
        hashes = [h.strip() for h in log_result.stdout.splitlines() if h.strip()]
        if not hashes:
            return ""

        sessions = []
        for h in hashes:
            show_result = subprocess.run(
                ["git", "show", f"{h}:{rel_path}"],
                capture_output=True, text=True, timeout=10, cwd=os.getcwd(),
            )
            if show_result.returncode != 0:
                continue
            try:
                data = _json.loads(show_result.stdout)
                task = data.get("task", "").strip()
                files = data.get("files_in_play", [])
                if task:
                    sessions.append({"task": task, "files": files[:5]})
            except Exception:
                pass

        if not sessions:
            return ""
        if len(sessions) == 1:
            return f"Last session: {sessions[0]['task']}"

        # Synthesise arc — oldest first so Haiku sees chronological progression
        history = "\n".join(
            f"Session {i+1}: {s['task']}" +
            (f" (files: {', '.join(s['files'])})" if s["files"] else "")
            for i, s in enumerate(reversed(sessions))
        )
        from askr.clients.claude import call_claude
        arc = call_claude(
            "You summarise developer session history in one sentence.",
            f"Recent sessions (oldest first):\n{history}\n\n"
            "In ONE sentence, describe what this developer has been building toward "
            "and where their momentum points. Be specific about the codebase area. "
            "No preamble.",
            mode="default",
            query_preview="session arc synthesis",
        )
        return arc.strip() if arc else ""
    except Exception:
        return ""


def _write_notification(trigger: str, goal: str = "", pct: float = 0.0, handover_ready: bool = False, project_path: str = "", handover_path: str = ""):
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
        if project_path:
            payload["allowed_tools"] = _load_allowed_tools(project_path)
        if goal:
            payload["prompt"] = f"Read the handover and start on the Next Action immediately. Work on: {goal}. Work autonomously."
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Trigger execution
# ---------------------------------------------------------------------------

def _notify_discord_resumed(trigger: str, goal: str):
    try:
        from askr.clients.discord import send_message
        reason = "context limit reached" if trigger == "context" else "quota reset"
        goal_str = f" Picking up: {goal}" if goal else ""
        send_message(f"**[askr] Session resumed** — {reason}.{goal_str}")
    except Exception:
        pass


def _write_resumed_marker(trigger: str, saved_seconds: int):
    try:
        _RESUMED_PATH = os.path.expanduser("~/.config/askr/resumed.json")
        os.makedirs(os.path.dirname(_RESUMED_PATH), exist_ok=True)
        with open(_RESUMED_PATH, "w") as f:
            import json as _json
            _json.dump({"trigger": trigger, "saved_seconds": saved_seconds}, f)
    except Exception:
        pass


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
    _write_notification(trigger, next_goal, pct, handover_has_content, project_path, result.get("handover_path", ""))
    _kill_claude(project_path)

    if trigger == "quota":
        reset_at = stats.get("quota_reset_at")
        if reset_at:
            _wait_for_reset(reset_at)
        else:
            time.sleep(300)

    _log("starting new claude session")
    launched = _start_claude(project_path)
    if launched:
        _notify_discord_resumed(trigger, next_goal)
    try:
        from askr.state.analytics import today_summary
        saved = today_summary().get("total_seconds", 0)
        _write_resumed_marker(trigger, saved)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------

def _pre_kill_update_tools(project_path: str):
    """
    Before killing Claude, extract all tools used in the active JSONL and
    persist them to the project's .claude/settings.json allowedTools.
    This ensures the new session inherits full permissions even if SIGKILL
    prevents the Stop hook from running _update_allowed_tools.
    """
    try:
        from askr.session.monitor import _find_active_jsonl
        jsonl = _find_active_jsonl(project_path)
        if not jsonl or not os.path.exists(jsonl):
            return
        tools_used = set()
        with open(jsonl) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "assistant":
                    continue
                for block in obj.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        if name:
                            tools_used.add(name)
        if not tools_used:
            return
        project_dir = os.path.join(project_path, ".claude")
        settings_path = os.path.join(project_dir, "settings.json")
        try:
            if os.path.exists(settings_path):
                with open(settings_path) as f:
                    settings = json.load(f)
            else:
                settings = {}
            existing = set(settings.get("allowedTools", []))
            merged = sorted(existing | tools_used)
            if merged != sorted(existing):
                settings["allowedTools"] = merged
                os.makedirs(project_dir, exist_ok=True)
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=2)
                _log(f"pre-kill: wrote {len(merged)} allowedTools to {settings_path}")
        except Exception as e:
            _log(f"pre-kill tool update failed: {e}")
        # permissions.allow in settings.local.json is what actually silences prompts
        local_path = os.path.join(project_dir, "settings.local.json")
        try:
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
                _log(f"pre-kill: wrote {len(tools_used)} tools to permissions.allow in {local_path}")
        except Exception as e:
            _log(f"pre-kill permissions.allow update failed: {e}")
    except Exception as e:
        _log(f"pre-kill update error: {e}")


def _wait_for_stop_hook_or_fallback(project_path: str):
    """
    After killing Claude, wait up to 20s for the Stop hook to consume
    checkpoint_pending.json (which means it ran, created the checkpoint,
    and wrote notification.json). If it's still there, the Stop hook didn't
    fire (likely SIGKILL) — handle the restart directly.
    """
    WAIT = 20
    for _ in range(WAIT):
        time.sleep(1)
        if not os.path.exists(_CHECKPOINT_PENDING):
            _log("Stop hook consumed checkpoint_pending — restart delegated to extension")
            return
    # Stop hook didn't run — do it ourselves, but only if Claude is actually dead.
    # If the kill failed (PID mismatch, timing), the original session is still alive.
    # Opening a new session alongside it causes dual-session chaos.
    still_alive = _read_claude_pid() or _find_claude_pid_by_project(project_path)
    if still_alive:
        _log(f"Claude pid {still_alive} still running after kill attempt — skipping fallback launch to prevent double-session")
        _clear_checkpoint_pending()
        return

    _log("Stop hook didn't fire after kill — running checkpoint + restart directly")
    _clear_checkpoint_pending()
    checkpoint_result = {}
    try:
        from askr.state.config import load_developer
        from askr.session.checkpoint import create_checkpoint
        developer = load_developer()
        state_dir = os.path.join(project_path, "askr_state") if os.path.isdir(os.path.join(project_path, "askr_state")) else None
        checkpoint_result = create_checkpoint(trigger_type="context", developer=developer, state_dir=state_dir)
        _log(f"daemon fallback checkpoint: {checkpoint_result.get('trigger')} at {checkpoint_result.get('timestamp','')[:19]}")
    except Exception as e:
        _log(f"daemon fallback checkpoint error: {e}")
    next_goal = _get_next_goal()
    _write_launch_mode(next_goal)
    allowed_tools = _load_allowed_tools(project_path)
    goal_part = f" Work on: {next_goal}." if next_goal else ""
    daemon_prompt = f"Read the handover and start on the Next Action immediately.{goal_part} Work autonomously."
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump({
                "type": "context",
                "message": "Context limit — Stop hook didn't fire. State saved to git. Opening new chat.",
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": daemon_prompt,
                "shown": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
        _log("daemon fallback: wrote notification.json — extension will open new terminal")
    except Exception as e:
        _log(f"daemon fallback notification error: {e}")
    # Also spawn Terminal.app fallback in case extension isn't active
    _start_claude(project_path)


def _wait_for_exchange_end_then_kill(project_path: str):
    """
    Poll the active JSONL file's mtime. Once it hasn't changed for IDLE_SECS,
    the current exchange is done — kill Claude so the Stop hook fires and
    consumes checkpoint_pending.json to run the checkpoint.

    No hard timeout: extended-thinking turns can run for 10+ minutes and must
    not be killed mid-API-call. PreCompact is the backstop for sessions that
    blow past the threshold in a single turn — it fires at a clean turn
    boundary, never mid-thinking.
    """
    IDLE_SECS = 20   # seconds of JSONL silence → exchange is done
    POLL      = 5

    _log("waiting for exchange to finish before killing Claude...")
    last_mtime = None
    idle_since = None

    while True:
        time.sleep(POLL)

        # If Claude exited on its own (user stopped it, crash, etc.), nothing to kill
        if _read_claude_pid() is None:
            _log("claude process gone during exchange wait — skipping kill")
            return

        # Hard override: if context is within striking distance of auto-compact,
        # kill immediately regardless of exchange state. Active human conversation
        # can continue in the new session via handover; losing in-progress output
        # is better than letting auto-compact destroy the session silently.
        try:
            from askr.session.monitor import stats_path_for_project
            stats_path = stats_path_for_project(project_path)
            with open(stats_path) as _sf:
                current_ctx = json.load(_sf).get("context_pct", 0)
            if current_ctx >= 0.80:
                _log(f"context at {current_ctx:.1%} — compaction imminent, killing now without waiting for idle")
                _pre_kill_update_tools(project_path)
                _kill_claude(project_path)
                _wait_for_stop_hook_or_fallback(project_path)
                return
        except Exception:
            pass

        try:
            sessions_dir = os.path.join(
                os.path.expanduser("~/.claude/projects"),
                project_path.replace("/", "-"),
            )
            files = [
                os.path.join(sessions_dir, f)
                for f in os.listdir(sessions_dir)
                if f.endswith(".jsonl")
            ] if os.path.isdir(sessions_dir) else []
            jsonl = max(files, key=os.path.getmtime) if files else None
            mtime = os.path.getmtime(jsonl) if jsonl else None
        except Exception:
            mtime = None

        if mtime is None:
            continue

        if mtime != last_mtime:
            last_mtime = mtime
            idle_since  = time.time()
        elif idle_since and (time.time() - idle_since) >= IDLE_SECS:
            _log(f"exchange idle for {IDLE_SECS}s — killing Claude to trigger Stop hook")
            _pre_kill_update_tools(project_path)
            _kill_claude(project_path)
            _wait_for_stop_hook_or_fallback(project_path)
            return


def _maybe_autolaunch(project_path: str):
    """If goals exist and no session is running, start Claude autonomously."""
    if not _claude_cli_available():
        return
    try:
        from askr.state.goals import load_today_goals
        goals = load_today_goals()
        if not goals:
            return
    except Exception:
        return
    goal = goals[0]
    _log(f"idle with open goals — auto-launching for: {goal}")
    _write_launch_mode(goal)
    _start_claude(project_path)


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
            fallback_path = load_project_path()

            active = _session_is_active()

            if active and not was_active:
                _log(f"session active")
                _start_caffeinate()
            elif not active and was_active:
                _log("session ended or went idle")
                _stop_caffeinate()

            was_active = active

            if active:
                stats = _read_stats()
                if stats:
                    # Each project writes its own stats file — no cross-project contamination.
                    # _read_stats() already picked the most recently active file.
                    project_path = stats.get("project_path") or fallback_path

                    ctx_pct    = stats.get("context_pct", 0)
                    ctx_label  = stats.get("context_label", "ok")
                    quota_pct  = stats.get("quota_pct")    # real % from /api/oauth/usage
                    reset_at   = stats.get("quota_reset_at", "")

                    in_cooldown = (time.time() - last_trigger_at) < TRIGGER_COOLDOWN

                    if in_cooldown:
                        remaining = int(TRIGGER_COOLDOWN - (time.time() - last_trigger_at))
                        _log(f"cooldown: {remaining}s remaining — ctx={ctx_pct:.1%} quota={quota_pct or 0:.1f}%")
                    elif ctx_pct >= CONTEXT_TRIGGER:
                        _log(f"Trigger A: context={ctx_pct:.1%} — waiting for exchange to finish, then killing Claude")
                        _write_checkpoint_pending(stats)
                        last_trigger_at = time.time()
                        _wait_for_exchange_end_then_kill(project_path)
                    elif quota_pct is not None and quota_pct >= QUOTA_TRIGGER:
                        _log(f"Trigger B: quota={quota_pct:.1f}% (real API)")
                        _execute_trigger("quota", stats, project_path)
                        last_trigger_at = time.time()
                    else:
                        q_str = f"quota={quota_pct:.1f}%" if quota_pct is not None else "quota=?"
                        _log(f"ok: ctx={ctx_pct:.1%} [{ctx_label}] {q_str} project={project_path}")

                time.sleep(POLL_ACTIVE)
            else:
                time.sleep(POLL_IDLE)

            # Source self-watch: if any .py file in the askr package changed since
            # startup, exit cleanly. launchd KeepAlive:true restarts us with the
            # new code — no manual daemon restart needed after a git pull.
            if _max_source_mtime() > _STARTUP_SOURCE_MTIME:
                _log("source files updated — exiting for launchd restart")
                # If extension.js also changed, prompt the user to reload their IDE
                if _extension_mtime() > _STARTUP_EXTENSION_MTIME:
                    try:
                        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
                        with open(_NOTIFICATION_PATH, "w") as f:
                            json.dump({
                                "type": "reload_extension",
                                "message": "askr updated — reload your IDE window to activate the new extension.",
                                "shown": False,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }, f)
                    except Exception:
                        pass
                _stop_caffeinate()
                _clear_pid()
                sys.exit(0)

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
