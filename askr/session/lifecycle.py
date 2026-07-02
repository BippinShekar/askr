#!/usr/bin/env python3
"""
Session Lifecycle Daemon

Installed as a launchd service by `askr init`. Starts at login, runs silently.

Session liveness: detected from ~/.config/askr/session_stats.json mtime.
  active = updated within last 10 minutes (Claude session running)
  idle   = stale or missing (no session)

Never kills or interrupts the user's live Claude session. It only ever opens a
fresh companion session alongside the running one and lets the user decide when
(or whether) to switch over — the old kill-then-relaunch design could yank a
session out from under the user mid-task.

Trigger A — context >= 60%:
  Read from session_stats.json (accurate: parsed from JSONL token counts)
  safe_pause check → checkpoint (live transcript, no kill) → open companion session

Trigger B — quota >= 90%:
  Read from session_stats.json (accurate: from Anthropic's /api/oauth/usage endpoint)
  safe_pause check → checkpoint → sleep until reset → open companion session
  (existing session, if still running, is left untouched throughout)
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
import glob
import time
import signal
import shlex
import shutil
import subprocess
from datetime import datetime, timezone

_PID_PATH              = os.path.expanduser("~/.config/askr/daemon.pid")
_CAFFEINATE_PID_PATH   = os.path.expanduser("~/.config/askr/caffeinate.pid")
_STATS_PATH            = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH      = os.path.expanduser("~/.config/askr/launch_mode.json")
_NOTIFICATION_PATH     = os.path.expanduser("~/.config/askr/notification.json")
_LOG_PATH              = os.path.expanduser("~/.config/askr/daemon.log")
_TRIGGER_STATE_PATH    = os.path.expanduser("~/.config/askr/trigger_state.json")
_COMPANIONED_SESSIONS_PATH = os.path.expanduser("~/.config/askr/companioned_sessions.json")
_QUOTA_WARNED_SESSIONS_PATH = os.path.expanduser("~/.config/askr/quota_warned_sessions.json")

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

POLL_ACTIVE        = 15    # seconds when session is live
POLL_IDLE          = 60    # seconds when no session
SESSION_STALE_SECS = 600   # 10 min without stats update → session ended
SAFE_RETRY_LIMIT   = 3
SAFE_RETRY_WAIT    = 60
CONTEXT_TRIGGER    = 0.60  # fire at 60% — 40% runway to auto-compact; earlier than 65% to survive extended-thinking spikes
QUOTA_TRIGGER      = 90.0  # fire when 5h quota reaches 90% (real API %)
QUOTA_WARNING_TRIGGER = 75.0  # heads-up spoken warning before the 90% hard trigger; fires once per session
TRIGGER_COOLDOWN   = 300   # seconds after a successful kill before re-firing
TRIGGER_MISS_COOLDOWN = 60 # seconds when trigger fired but Claude PID was not found


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


def _read_all_stats() -> list:
    """Return stats for ALL active projects with a recent stats file."""
    try:
        if not os.path.isdir(_STATS_DIR):
            return []
        now = time.time()
        results = []
        for f in os.listdir(_STATS_DIR):
            if not f.endswith(".json"):
                continue
            path = os.path.join(_STATS_DIR, f)
            if now - os.path.getmtime(path) >= SESSION_STALE_SECS:
                continue
            try:
                with open(path) as fp:
                    data = json.load(fp)
                ua = data.get("updated_at", "")
                if ua:
                    age = (datetime.now(timezone.utc) - datetime.fromisoformat(ua)).total_seconds()
                    if age > SESSION_STALE_SECS:
                        continue
                results.append(data)
            except Exception:
                continue
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Claude process management
# ---------------------------------------------------------------------------

def _claude_cli_available() -> bool:
    return shutil.which("claude") is not None


def _terminal_app_fallback_worker(project_path: str, claude_bin: str, tools_flag: str,
                                   safe_prompt: str, notif_path: str, delay: int = 20):
    """
    Runs in a detached subprocess. Waits `delay` seconds, then opens Terminal.app
    and types the prompt — UNLESS the extension already claimed the notification
    (notif.shown == True, which it sets synchronously the moment it reads the file,
    well before this delay elapses in the common case).

    Used to also skip if ANY claude process existed for this project — that was a
    valid secondary guard back when askr killed the old session before relaunching
    (a live pid meant "something already relaunched"). Now askr deliberately opens
    a companion session ALONGSIDE the user's still-running one, so a live pid for
    this project is the normal, expected state and says nothing about whether the
    companion has been opened yet. Relying on that check would silently block this
    fallback for any user not running the IDE extension. The `shown` flag above is
    the only reliable signal now.
    """
    import time as _time
    _time.sleep(delay)
    try:
        with open(notif_path) as f:
            if json.load(f).get("shown"):
                return
    except Exception:
        pass

    start_cmd = f'cd {project_path} && {claude_bin}{tools_flag}'
    open_script = 'tell application "Terminal"\n  do script "' + start_cmd + '"\n  activate\nend tell'
    subprocess.run(["osascript", "-e", open_script], timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _time.sleep(10)
    type_script = ('tell application "Terminal"\n  tell front window\n'
                    f'    keystroke {safe_prompt!r}\n    key code 36\n  end tell\nend tell')
    subprocess.run(["osascript", "-e", type_script], timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _spawn_terminal_app_fallback(project_path: str, claude_bin: str, tools_flag: str,
                                  safe_prompt: str, notif_path: str):
    """Spawn _terminal_app_fallback_worker in a detached process so it survives this process exiting."""
    try:
        code = (
            f"import sys; sys.path.insert(0, {_ASKR_ROOT!r})\n"
            f"from askr.session.lifecycle import _terminal_app_fallback_worker as w\n"
            f"w({project_path!r}, {claude_bin!r}, {tools_flag!r}, {safe_prompt!r}, {notif_path!r})\n"
        )
        subprocess.Popen(
            [sys.executable, "-c", code],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        _log("fallback watcher spawned — Terminal.app fires in 20s if extension doesn't handle it")
    except Exception as e:
        _log(f"fallback watcher spawn failed: {e}")


def _find_all_claude_pids_by_project(project_path: str) -> list[int]:
    """Find ALL running 'claude' processes whose cwd matches project_path."""
    pids = []
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
                        pids.append(pid)
                        break
            except Exception:
                continue
    except Exception:
        pass
    return pids


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


def _start_claude(project_path: str, initial_prompt: str = "", force: bool = False) -> bool:
    if not _claude_cli_available():
        _log("ERROR: 'claude' not in PATH — cannot start new session")
        return False

    # Refuse to open a new session if Claude is already running for this project —
    # UNLESS force=True, which trigger paths use deliberately: askr now opens a
    # companion session alongside the user's live one instead of killing it first,
    # so "already running" is expected, not a double-launch bug.
    if not force:
        existing = _find_all_claude_pids_by_project(project_path)
        if existing:
            _log(f"Claude pid(s) {existing} already running for {project_path} — skipping launch to prevent double-session")
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

    # Spawn a detached watcher: after a delay, check if the extension marked the
    # notification shown AND re-check for a live claude process before falling
    # back to Terminal.app — see _terminal_app_fallback_worker for why both checks
    # happen after the wait, not before.
    safe_prompt = prompt_arg.replace("'", "").replace('"', "").replace("\\", "")
    _spawn_terminal_app_fallback(project_path, claude_bin, tools_flag, safe_prompt, _NOTIFICATION_PATH)
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


def _get_next_goal(state_dir: str = None) -> str:
    try:
        from askr.state.goals import load_today_goals, load_open_goals
        today = load_today_goals(state_dir)
        if today:
            return today[0]
        return (load_open_goals(state_dir) or [""])[0]
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




def _infer_direction(project_path: str = "") -> dict:
    """
    Infer what the next autonomous session should work on from deterministic signals.

    Signal priority (highest confidence first):
      1. Uncommitted files       — work was interrupted mid-session (confidence 0.95)
      2. blockers.md             — something is explicitly stuck (confidence 0.90)
      3. Handover next_actions   — previous session already planned the next step (confidence 0.85)
      4. Conventional commit scope — most active subsystem in last 10 commits (confidence 0.56-0.72)
      5. Nothing                 — no signal found (confidence 0.35)

    Returns {direction, confidence, signal_source, details}
    Never raises — all errors produce the low-confidence fallback.
    """
    import re as _re
    cwd = project_path or os.getcwd()

    # Signal 1: uncommitted files — work was cut mid-sentence
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

    # Signal 2: an active blocker — either auto-recorded in a per-dev handover
    # JSON (race-free, no shared file) or manually noted in blockers.md.
    try:
        entries = []
        for path in glob.glob(os.path.join(cwd, "askr_state", "handover_*.json")):
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                continue
            entries.extend(data.get("blockers") or [])

        blockers_path = os.path.join(cwd, "askr_state", "blockers.md")
        if os.path.exists(blockers_path):
            content = open(blockers_path).read().strip()
            _skip = {"none noted", "[none]", "none"}
            entries.extend(
                l.strip() for l in content.splitlines()
                if l.strip()
                and not l.startswith("#")
                and not l.lower().startswith("last updated")
                and l.strip().lower() not in _skip
            )

        if entries:
            return {
                "direction": f"resolve blocker: {entries[0][:120]}",
                "confidence": 0.90,
                "signal_source": "blockers",
                "details": entries,
            }
    except Exception:
        pass

    # Signal 3: next_actions from the most recent handover that has a concrete direction.
    #
    # Walk handover commit history. For each pair of consecutive handover commits,
    # check whether non-askr_state files changed between them:
    #
    #   CODING session  → auto-launch (proposed=False): direction is grounded in committed work
    #   TALK-ONLY session with next_actions → propose to user (proposed=True): research or
    #       strategy sessions can still conclude with a real implementation directive; surface
    #       it for approval rather than discarding it or auto-launching blind
    #   TALK-ONLY session with empty next_actions → skip, keep looking
    #
    # First match (coding or talk-only-with-direction) wins.
    try:
        import json as _json
        from askr.state.config import load_developer, state_path
        dev = load_developer()
        handover_rel = f"askr_state/handover_{dev}.json"

        log_result = subprocess.run(
            ["git", "log", "--format=%H", "-10", "--", handover_rel],
            capture_output=True, text=True, timeout=10, cwd=cwd,
        )
        hashes = log_result.stdout.strip().splitlines()

        for i in range(len(hashes) - 1):
            curr_hash, prev_hash = hashes[i], hashes[i + 1]

            diff_result = subprocess.run(
                ["git", "diff", "--name-only", prev_hash, curr_hash],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            code_files = [
                l.strip() for l in diff_result.stdout.splitlines()
                if l.strip() and not l.startswith("askr_state/")
            ]
            is_coding = bool(code_files)

            # Read this session's handover from git
            show_result = subprocess.run(
                ["git", "show", f"{curr_hash}:{handover_rel}"],
                capture_output=True, text=True, timeout=10, cwd=cwd,
            )
            if show_result.returncode != 0:
                continue
            handover = _json.loads(show_result.stdout)
            actions = handover.get("next_actions", [])
            if not actions:
                # No direction from this session — keep looking regardless of type
                continue
            first = actions[0]
            action_text = first.get("action") if isinstance(first, dict) else str(first)
            if not action_text or len(action_text) < 10:
                continue

            # Talk-only with no direction: already filtered above by `not actions` /
            # short action_text. If we reach here, there IS a direction.
            # Coding → auto-launch. Talk-only → propose to user.
            return {
                "direction": action_text[:200],
                "confidence": 0.85,
                "signal_source": "handover_next_actions",
                "proposed": not is_coding,  # True = surface for approval, False = auto-launch
                "details": {
                    "commit": curr_hash[:7],
                    "session_type": "coding" if is_coding else "talk_only",
                    "developer": dev,
                },
            }
    except Exception:
        pass

    # Signal 4: conventional commit scopes — tells you the subsystem, not the repo root
    # Falls back to second-level path grouping if no conventional commits found.
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--name-only", "-10"],
            capture_output=True, text=True, timeout=10, cwd=cwd,
        )
        _commit_re = _re.compile(r'^[0-9a-f]{7,} ')
        _scope_re  = _re.compile(r'\b\w+\(([^)]+)\):')  # feat(scope): / fix(scope):
        from collections import Counter
        scopes: Counter = Counter()
        paths:  Counter = Counter()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("askr_state"):
                continue
            if _commit_re.match(line):
                # Commit message line — extract conventional scope
                m = _scope_re.search(line)
                if m:
                    scopes[m.group(1)] += 1
            else:
                # File path line — track second-level component as fallback
                parts = line.split("/")
                key = "/".join(parts[:2]) if len(parts) >= 2 else parts[0]
                paths[key] += 1

        if scopes:
            top_scope, count = scopes.most_common(1)[0]
            confidence = min(0.72, 0.50 + count * 0.075)  # 1 hit=0.58, 3 hits=0.72
            return {
                "direction": f"continue work on {top_scope} ({count} of last 10 commits)",
                "confidence": round(confidence, 2),
                "signal_source": "commit_scope",
                "details": dict(scopes.most_common(5)),
            }

        if paths:
            top_path, count = paths.most_common(1)[0]
            confidence = min(0.60, 0.42 + count * 0.04)
            return {
                "direction": f"continue work in {top_path}/ ({count} recent changes)",
                "confidence": round(confidence, 2),
                "signal_source": "file_path_cluster",
                "details": dict(paths.most_common(5)),
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
            "project_path": project_path,
            "shown": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if project_path:
            payload["allowed_tools"] = _load_allowed_tools(project_path)
        if goal:
            payload["prompt"] = f"Read the handover and start on the Next Action immediately. Work on: {goal}. Work autonomously."
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
        _speak(msg)
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

    state_dir = os.path.join(project_path, "askr_state")
    if not os.path.isdir(state_dir):
        _log(f"WARN: no askr_state/ in {project_path} — skipping checkpoint (run 'askr init' there first)")
        return

    _log("safe to pause — creating checkpoint")
    from askr.session.monitor import _find_active_jsonl
    transcript_path = _find_active_jsonl(project_path) or ""
    result = create_checkpoint(trigger_type=trigger, developer=developer,
                                transcript_path=transcript_path, state_dir=state_dir)
    _log(f"checkpoint: {result.get('trigger')} at {result.get('timestamp', '')[:19]}")

    next_goal = _get_next_goal(state_dir)
    _write_launch_mode(next_goal)
    pct = stats.get("context_pct", 0.0) if trigger == "context" else stats.get("quota_pct", 0.0)
    handover_path = result.get("handover_path", "")
    handover_has_content = bool(handover_path and os.path.exists(handover_path) and
                                os.path.getsize(handover_path) > 200)
    _write_notification(trigger, next_goal, pct, handover_has_content, project_path, result.get("handover_path", ""))
    # Never kill the user's live session — just prepare a companion one. The old
    # kill-then-relaunch design could yank a running session out from under the
    # user mid-task; askr now only ever adds a fresh session, never removes theirs.

    if trigger == "quota":
        reset_at = stats.get("quota_reset_at")
        if reset_at:
            _wait_for_reset(reset_at)
        else:
            time.sleep(300)

    _log("starting companion claude session (existing session, if any, left running)")
    launched = _start_claude(project_path, force=True)
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


def _open_companion_session(project_path: str, session_id: str = None):
    """
    Checkpoint the live session's current state and open a fresh, low-context
    companion session alongside it — WITHOUT touching the running one.

    Replaces the old kill-then-relaunch flow. askr used to SIGTERM the user's
    live session before opening a new one — that could yank a session out from
    under the user mid-task, which is bad UX regardless of how well-intentioned
    the context-management reasoning is. Now askr only ever adds a session; the
    existing one keeps running for as long as the user wants it, and the user
    decides when (or whether) to switch over.
    """
    _pre_kill_update_tools(project_path)  # sync allowedTools/permissions for the new session

    state_dir = os.path.join(project_path, "askr_state")
    try:
        from askr.state.config import load_developer
        from askr.session.checkpoint import create_checkpoint
        from askr.session.monitor import _find_active_jsonl
        developer = load_developer()
        if not os.path.isdir(state_dir):
            raise RuntimeError(f"no askr_state/ in {project_path} — run 'askr init' there first")
        # _find_active_jsonl picks by mtime, not liveness — reads the live
        # session's transcript without needing to kill it first.
        transcript_path = _find_active_jsonl(project_path) or ""
        checkpoint_result = create_checkpoint(
            trigger_type="context", developer=developer,
            transcript_path=transcript_path, state_dir=state_dir,
        )
        _log(f"checkpoint (companion session): {checkpoint_result.get('trigger')} at {checkpoint_result.get('timestamp','')[:19]}")
    except Exception as e:
        _log(f"companion checkpoint error: {e}")

    next_goal = _get_next_goal(state_dir)
    _write_launch_mode(next_goal)
    allowed_tools = _load_allowed_tools(project_path)

    daemon_prompt = ""
    try:
        direction = _infer_direction(project_path)
        if direction["confidence"] >= 0.70:
            daemon_prompt = (
                f"Continue work on: {direction['direction']}. Read the handover file "
                f"for the full state. Your previous session is still running in another "
                f"window — pick up from the handover, don't redo work already in flight there."
            )
    except Exception:
        pass
    if not daemon_prompt:
        goal_part = f" Work on: {next_goal}." if next_goal else ""
        daemon_prompt = f"Read the handover and start on the Next Action immediately.{goal_part} Work autonomously."

    try:
        companion_message = "Context high on your current session — a fresh companion session is ready. Your current one keeps running."
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump({
                "type": "context",
                "message": companion_message,
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": daemon_prompt,
                "shown": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
        _log("wrote notification.json — extension will open a NEW terminal; existing session left running")
        _speak(companion_message)
    except Exception as e:
        _log(f"companion notification error: {e}")

    # Don't call _start_claude here — force=True bypasses its double-session guard,
    # but that guard exists for the goal-autolaunch path which should still refuse
    # when something's already running. Spawn the terminal directly instead.
    claude_bin  = shutil.which("claude") or "claude"
    tools_flag  = f" --allowedTools {','.join(allowed_tools)}" if allowed_tools else ""
    safe_prompt = daemon_prompt.replace("'", "").replace('"', "").replace("\\", "")
    _spawn_terminal_app_fallback(project_path, claude_bin, tools_flag, safe_prompt, _NOTIFICATION_PATH)


_TURN_STOP_DIR = os.path.expanduser("~/.config/askr/turn_stops")


def _turn_stopped_since(session_id: str, since_ts: float) -> bool:
    """True once stop.py has signaled turn completion for this session_id after since_ts."""
    if not session_id:
        return False
    marker = os.path.join(_TURN_STOP_DIR, f"{session_id}.json")
    return os.path.exists(marker) and os.path.getmtime(marker) >= since_ts


def _open_companion_session_for_trigger(project_path: str, session_id: str = None) -> bool:
    """
    Context trigger fired. Wait for the current Claude reply to finish before
    opening the companion session — the user must always get their complete reply
    before a second window appears.

    "Reply finished" is detected via the Stop hook's own completion signal
    (askr/hooks/stop.py writes ~/.config/askr/turn_stops/<session_id>.json when it
    finishes processing a turn) — not JSONL write-silence. The old idle-time
    heuristic false-positived whenever a tool call ran long enough to pause JSONL
    writes for IDLE_THRESHOLD seconds (e.g. a multi-minute git-filter-repo run),
    opening a companion session while the original turn was still very much in
    progress. The Stop hook firing is the only authoritative "turn is done" signal.

    Returns True if a live session was found (full cooldown applies), False if
    no live process was detected (short retry).
    """
    if not _find_all_claude_pids_by_project(project_path):
        _log("claude process not found for this project — opening companion session anyway")
        _open_companion_session(project_path, session_id)
        return False

    POLL          = 5    # polling interval (seconds)
    MAX_WAIT_SECS = 600  # hard cap; only hit if the Stop hook never fires (runaway turn)

    _log("waiting for current reply to finish (watching for Stop hook signal)...")

    wait_start = time.time()
    waited = 0

    while True:
        time.sleep(POLL)
        waited += POLL

        if not _find_all_claude_pids_by_project(project_path):
            _log("claude session ended while waiting — opening companion session")
            break

        if _turn_stopped_since(session_id, wait_start):
            _log("Stop hook fired — reply finished, opening companion session")
            break

        if waited >= MAX_WAIT_SECS:
            _log(f"WARN: waited {MAX_WAIT_SECS}s, Stop hook never fired — opening companion session anyway")
            break

    _open_companion_session(project_path, session_id)
    return True


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


def _load_trigger_state() -> dict:
    """
    Disk-backed cooldown state — survives the source-watch self-restart.
    Without this, any code change (including the daemon editing its own source
    mid-session, or a co-founder's git pull landing a fix) wipes the in-memory
    last_trigger_at dict, instantly defeating the 300s cooldown and causing
    repeated kills against the same stale-stats-driven trigger.
    """
    try:
        with open(_TRIGGER_STATE_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_trigger_state(state: dict):
    try:
        os.makedirs(os.path.dirname(_TRIGGER_STATE_PATH), exist_ok=True)
        with open(_TRIGGER_STATE_PATH, "w") as f:
            json.dump(state, f)
    except Exception as e:
        # Silent failure here defeats the per-project cooldown — the same
        # trigger would re-fire every poll instead of respecting TRIGGER_COOLDOWN.
        _log(f"WARN: failed to persist trigger state: {e}")


def _load_companioned_sessions() -> set:
    """
    Session-ids that have already had a companion session opened for them.

    Without this, a session that crosses CONTEXT_TRIGGER and is never killed
    (by design — see module docstring) stays above the threshold for as long
    as it keeps running. The 300s cooldown is keyed by project_path, not
    session_id, so it expires and fires again against the SAME still-running
    session every cooldown window — spawning an unbounded number of companion
    terminals for one source session instead of just one.
    """
    try:
        with open(_COMPANIONED_SESSIONS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_companioned_sessions(sessions: set):
    try:
        os.makedirs(os.path.dirname(_COMPANIONED_SESSIONS_PATH), exist_ok=True)
        with open(_COMPANIONED_SESSIONS_PATH, "w") as f:
            json.dump(list(sessions), f)
    except Exception as e:
        # Silent failure here reintroduces the unbounded-companion-spawn bug
        # this set exists to prevent (see docstring above).
        _log(f"WARN: failed to persist companioned sessions: {e}")


def _load_quota_warned_sessions() -> set:
    """Session-ids already given the QUOTA_WARNING_TRIGGER heads-up — same
    one-per-session dedup idea as _load_companioned_sessions, otherwise the
    warning re-fires every poll for as long as a session sits above 75%."""
    try:
        with open(_QUOTA_WARNED_SESSIONS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_quota_warned_sessions(sessions: set):
    try:
        os.makedirs(os.path.dirname(_QUOTA_WARNED_SESSIONS_PATH), exist_ok=True)
        with open(_QUOTA_WARNED_SESSIONS_PATH, "w") as f:
            json.dump(list(sessions), f)
    except Exception as e:
        _log(f"WARN: failed to persist quota-warned sessions: {e}")


def _speak(message: str):
    try:
        from askr.clients.voice import announce
        announce(message)
    except Exception:
        pass


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
    last_trigger_at: dict = _load_trigger_state()  # project_path → epoch seconds, disk-backed (survives restarts)
    companioned_sessions: set = _load_companioned_sessions()  # session_id → already got a companion, disk-backed
    quota_warned_sessions: set = _load_quota_warned_sessions()  # session_id → already spoke the 75% heads-up, disk-backed

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
                # Scan ALL active projects every poll — not just the most recently updated one.
                # When two sessions run simultaneously (e.g. askr + leaps) each gets checked
                # independently. Triggers are handled sequentially; pre-compact is the backstop
                # for a second project that spikes while the first is being handled.
                all_stats = _read_all_stats()
                triggered_this_cycle = False

                # Sort highest context first so the most urgent project is handled first
                for stats in sorted(all_stats, key=lambda s: s.get("context_pct", 0), reverse=True):
                    project_path = stats.get("project_path") or fallback_path
                    ctx_pct   = stats.get("context_pct", 0)
                    ctx_label = stats.get("context_label", "ok")
                    quota_pct = stats.get("quota_pct")
                    reset_at  = stats.get("quota_reset_at", "")

                    proj_last = last_trigger_at.get(project_path, 0.0)
                    in_cooldown = (time.time() - proj_last) < TRIGGER_COOLDOWN
                    session_id = stats.get("session_id")
                    already_companioned = bool(session_id) and session_id in companioned_sessions

                    # Pre-emptive heads-up, independent of the trigger/cooldown state below —
                    # it doesn't checkpoint or open anything, just speaks once per session.
                    if (session_id and quota_pct is not None
                            and QUOTA_WARNING_TRIGGER <= quota_pct < QUOTA_TRIGGER
                            and session_id not in quota_warned_sessions):
                        _log(f"quota warning: {quota_pct:.1f}% (real API) [{project_path}] session={session_id[:8]}")
                        quota_warned_sessions.add(session_id)
                        _save_quota_warned_sessions(quota_warned_sessions)
                        _speak(f"Quota at {round(quota_pct)} percent. Consider wrapping up soon.")

                    if already_companioned and ctx_pct >= CONTEXT_TRIGGER:
                        # This exact session already got a companion. Since we never kill
                        # it, it stays above CONTEXT_TRIGGER for as long as it keeps
                        # running — the per-project cooldown alone would just expire and
                        # re-fire against this same session every 300s forever, stacking
                        # up an unbounded number of companion terminals. One companion
                        # per session, period, until that session actually ends.
                        _log(f"session {session_id[:8]} already has a companion open — not spawning another (ctx={ctx_pct:.1%})")
                    elif in_cooldown:
                        remaining = int(TRIGGER_COOLDOWN - (time.time() - proj_last))
                        _log(f"cooldown: {remaining}s remaining — ctx={ctx_pct:.1%} project={project_path}")
                    elif ctx_pct >= CONTEXT_TRIGGER:
                        _log(f"Trigger A: context={ctx_pct:.1%} — opening companion session [{project_path}] (existing session left running)")
                        if session_id:
                            companioned_sessions.add(session_id)
                            _save_companioned_sessions(companioned_sessions)
                        found = _open_companion_session_for_trigger(project_path, session_id)
                        if found:
                            # Full cooldown — companion opened alongside a live session
                            last_trigger_at[project_path] = time.time()
                        else:
                            # No live claude process — short cooldown so we retry quickly
                            # rather than waiting the full 5 minutes
                            last_trigger_at[project_path] = time.time() - TRIGGER_COOLDOWN + TRIGGER_MISS_COOLDOWN
                            _log(f"no live session found — retry in {TRIGGER_MISS_COOLDOWN}s")
                        _save_trigger_state(last_trigger_at)
                        triggered_this_cycle = True
                        break  # re-scan all projects next cycle after handling this one
                    elif quota_pct is not None and quota_pct >= QUOTA_TRIGGER:
                        _log(f"Trigger B: quota={quota_pct:.1f}% (real API) [{project_path}]")
                        _execute_trigger("quota", stats, project_path)
                        last_trigger_at[project_path] = time.time()
                        _save_trigger_state(last_trigger_at)
                        triggered_this_cycle = True
                        break
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
