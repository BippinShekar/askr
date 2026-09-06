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
import threading
from datetime import datetime, timedelta, timezone
from typing import Optional

_PID_PATH              = os.path.expanduser("~/.config/askr/daemon.pid")
_CAFFEINATE_PID_PATH   = os.path.expanduser("~/.config/askr/caffeinate.pid")
_STATS_PATH            = os.path.expanduser("~/.config/askr/session_stats.json")
_LAUNCH_MODE_PATH      = os.path.expanduser("~/.config/askr/launch_mode.json")
_NOTIFICATION_PATH     = os.path.expanduser("~/.config/askr/notification.json")
_LOG_PATH              = os.path.expanduser("~/.config/askr/daemon.log")
_TRIGGER_STATE_PATH    = os.path.expanduser("~/.config/askr/trigger_state.json")
_COMPANIONED_SESSIONS_PATH = os.path.expanduser("~/.config/askr/companioned_sessions.json")
# Despite the filename (kept for backward compat with existing installs), this now
# stores warned quota_reset_at timestamps, not session ids — see _load/_save below.
_QUOTA_WARNED_SESSIONS_PATH = os.path.expanduser("~/.config/askr/quota_warned_sessions.json")
# quota_reset_at timestamps that already had the 90% hard trigger fired — same
# dedup shape as _QUOTA_WARNED_SESSIONS_PATH, but for _execute_quota_trigger
# (which checkpoints, speaks, and waits for reset) rather than the pre-trigger heads-up.
_QUOTA_TRIGGERED_WINDOWS_PATH = os.path.expanduser("~/.config/askr/quota_triggered_windows.json")
# "session_id::reset_at" strings that have already had their own native-resume
# verification (Phase 4) run for this account-wide window. Separate from
# _QUOTA_TRIGGERED_WINDOWS_PATH on purpose (2026-09-06): that dedup correctly
# stops duplicate voice/Discord announcements when 2+ concurrent sessions
# share one account-wide quota window, but it was ALSO silently skipping the
# verify-and-cont step for every session except whichever fired the trigger
# first — confirmed live, a second session sharing the window sat frozen at
# its limit with nothing watching it. Keyed per-session, not per-window, so
# every concurrent session still gets its own resume check even when the
# announcement itself was already deduped away.
_QUOTA_RESUME_VERIFIED_PATH = os.path.expanduser("~/.config/askr/quota_resume_verified.json")
# project_path -> ISO turn-stop timestamp the idle trigger already fired for.
# Keyed by the turn-stop timestamp itself (not just a bool) so a brand new
# turn automatically makes the project eligible again — no separate pruning
# needed, unlike the quota dedup sets above which need reset-window pruning.
_IDLE_TRIGGERED_PATH = os.path.expanduser("~/.config/askr/idle_triggered.json")
_SESSION_FIRST_SEEN_PATH = os.path.expanduser("~/.config/askr/session_first_seen.json")
# session_id -> parent_session_id, best-effort lineage for the event log.
# Populated when a session_id is first observed in session_first_seen by
# reading whatever parent_session_id launch_mode.json currently holds (written
# by the SAME daemon process at companion-spawn time, moments earlier — see
# _write_launch_mode). launch_mode.json holds only one current value, so if
# multiple companions spawn in quick succession before the next one is
# observed, an in-between session could inherit the wrong parent. Acceptable:
# this is best-effort lineage for the event log, not a correctness-critical
# dedup key.
_SESSION_PARENT_PATH = os.path.expanduser("~/.config/askr/session_parent.json")

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
CONTEXT_TRIGGER    = 0.70  # fire at 70% — 30% runway to auto-compact
QUOTA_TRIGGER      = 90.0  # fire when 5h quota reaches 90% (real API %)
QUOTA_WARNING_TRIGGER = 75.0  # heads-up spoken warning before the 90% hard trigger; fires once per session
TRIGGER_COOLDOWN   = 300   # seconds after a successful kill before re-firing
TRIGGER_MISS_COOLDOWN = 60 # seconds when trigger fired but Claude PID was not found
ACTIVITY_GRACE_SECS = 60   # skip trigger evaluation for this long after a session_id is first observed —
                           # otherwise a brand-new session can inherit an already-high account-wide quota%
                           # from prior usage and get interrupted before the user has even sent one message
IDLE_TRIGGER_SECS   = SESSION_STALE_SECS  # genuine inactivity → run the heavy emergency checkpoint
                           # (git commit+push, architecture regen, Discord/voice). Reuses the same
                           # threshold askr already treats as "this session is effectively over"
                           # elsewhere, instead of a separately-invented number.
MAX_TURN_ACTIVE_SECS = 1800  # if a turn-start marker is older than this with no matching stop,
                           # AND there's no liveness signal (see _turn_marker_still_live) to trust
                           # it, treat the turn as abandoned (crashed session, closed terminal)
                           # rather than "still active" forever — otherwise a turn that never
                           # signals Stop would permanently suppress the idle-checkpoint safety net.
                           # Found 2026-08-10: this used to be an unconditional cutoff — ANY turn
                           # older than 30 min was flagged abandoned, including a genuine 50-minute
                           # single turn confirmed in production, which got misclassified as
                           # abandoned 20 minutes before it actually finished. A stuck marker and a
                           # long turn look identical by wall-clock age alone; liveness (process
                           # still running, transcript still being written to) is what actually
                           # tells them apart, so age alone now only starts the liveness check
                           # rather than deciding the answer by itself.
TURN_QUIET_GRACE_SECS = 90  # found 2026-07-14: Stop fires the instant Claude's reply finishes
                           # generating, even when that reply is a plain-text question waiting on
                           # the user (no tool call involved, so _turn_currently_active() has
                           # nothing to key off — from the turn markers' view the session is
                           # already "quiet"). A companion opening ~5s after Claude asks something
                           # is functionally the same interruption as opening mid-reply. Require
                           # this much real silence since the last Stop before treating the turn
                           # boundary as safe — long enough for a human to notice and start typing,
                           # far short of IDLE_TRIGGER_SECS (10 min), which answers a different
                           # question ("has this session been abandoned").


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
        # caffeinate -i only blocks IDLE sleep — it cannot prevent clamshell
        # (lid-close) sleep on a MacBook without an external display attached,
        # on battery OR on AC power. Confirmed live 2026-09-04: a quota-wait
        # thread correctly held this lock through "session ended or went
        # idle," but the machine still slept for 1h49m mid-wait and the
        # target claude process was SIGKILLed during the gap — not by askr.
        # Warn unconditionally; the old battery-only check implied AC power
        # was safe, which it isn't without a second display.
        _log("NOTE: caffeinate cannot prevent lid-close sleep without an external "
             "display attached — closing the lid during a quota wait can still "
             "suspend the machine for the whole wait, regardless of power source")
    except FileNotFoundError:
        _log("WARNING: caffeinate not found")
    except Exception as e:
        _log(f"caffeinate start failed: {e}")


def _stop_caffeinate():
    if _quota_wait_in_flight():
        # Confirmed live 2026-08-15: session went idle mid-quota-wait, this
        # unconditionally stopped caffeinate, the Mac slept, and the whole
        # daemon (all projects, all threads) froze for 1h43m — right through
        # the window _wait_until_quota_near_exhausted needed to actually
        # observe quota crossing 99% and interrupt the user. It only found
        # out the reset had already passed once it woke up hours later, so
        # no warning/notification/voice ever surfaced live. Don't release
        # the sleep lock while that wait (or the Stage 5 premature-activity
        # watch that follows it) is still running, regardless of session
        # idle state.
        _log("caffeinate stop skipped — quota-wait thread still in flight")
        return
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


# Tracks whether an _execute_quota_trigger thread (Phase 2 near-exhausted
# poll or the Stage 5 premature-activity watch) is currently in flight, so
# _stop_caffeinate() can refuse to release the sleep lock out from under it.
# A depth counter, not a bool: quota is account-wide but _evaluate_session_triggers
# runs per-project, so two projects can each be mid-wait at once.
_quota_wait_lock = threading.Lock()
_quota_wait_depth = 0


def _quota_wait_begin():
    global _quota_wait_depth
    with _quota_wait_lock:
        _quota_wait_depth += 1


def _quota_wait_end():
    global _quota_wait_depth
    with _quota_wait_lock:
        _quota_wait_depth = max(0, _quota_wait_depth - 1)


def _quota_wait_in_flight() -> bool:
    with _quota_wait_lock:
        return _quota_wait_depth > 0


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


def _applescript_quote(s: str) -> str:
    """Escape and wrap a string as a safe AppleScript double-quoted literal.

    Without this, a project_path or prompt containing a `"` breaks out of the
    `do script "..."` / `keystroke "..."` string boundary — and since `do script`
    runs its argument as a real shell command in Terminal.app, that's a command
    injection, not just a syntax error.
    """
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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

    # shlex.quote guards the shell layer (project_path could contain ; $() ` etc),
    # _applescript_quote guards the AppleScript string layer (a literal " would
    # otherwise close the do-script string early) — both are needed, independently.
    start_cmd = f'cd {shlex.quote(project_path)} && {claude_bin}{tools_flag}'
    open_script = 'tell application "Terminal"\n  do script ' + _applescript_quote(start_cmd) + '\n  activate\nend tell'
    subprocess.run(["osascript", "-e", open_script], timeout=5,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _time.sleep(10)
    type_script = ('tell application "Terminal"\n  tell front window\n'
                    f'    keystroke {_applescript_quote(safe_prompt)}\n    key code 36\n  end tell\nend tell')
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


def _get_ancestor_pids(pid: int, max_depth: int = 6) -> list:
    """
    Walk the process tree upward from `pid` (a `claude` process), returning
    its ancestor PIDs in order (immediate parent first). Built for the
    same-session rate-limit-resume feature: a VS Code/Cursor integrated
    terminal exposes `terminal.processId` (the shell PID) but has no concept
    of a "Claude session_id" — this is the other half of the bridge, giving
    the extension a set of PIDs to match `terminal.processId` against rather
    than needing to identify which ancestor is specifically "the shell."
    Any one of these matching is sufficient — extra layers (a wrapper, tmux,
    etc.) don't need to be specifically identified, just present in the set.

    Stops at max_depth or once ppid <= 1 (reached init/launchd). Never
    raises — a broken `ps` call just yields a shorter (possibly empty) list,
    which the caller treats as "no match found," not an error.
    """
    ancestors = []
    current = pid
    for _ in range(max_depth):
        try:
            result = subprocess.run(
                ["ps", "-o", "ppid=", "-p", str(current)],
                capture_output=True, text=True, timeout=3,
            )
            ppid_str = result.stdout.strip()
            if not ppid_str:
                break
            ppid = int(ppid_str)
        except Exception:
            break
        if ppid <= 1:
            break
        ancestors.append(ppid)
        current = ppid
    return ancestors


def _norm_path(path: str) -> str:
    """
    Resolve symlinks/case before comparing paths across process boundaries.
    macOS mounts the boot volume at both `/Users/...` and the underlying
    `/System/Volumes/Data/Users/...` — `lsof -d cwd` reports whichever form
    the kernel resolved to, which doesn't always match the form callers built
    project_path from (os.getcwd(), a hook payload's cwd, etc). A bare string
    equality against unresolved paths silently undercounts live pids, which
    is exactly what let pre_compact.py's companion-dedup guard open a
    redundant companion on top of one already running (confirmed live
    2026-08-18: _find_all_claude_pids_by_project missed an already-running
    pid whose lsof cwd and the caller's project_path took different forms of
    the same real directory).
    """
    try:
        return os.path.realpath(path)
    except Exception:
        return path


def _find_session_pid(transcript_path: str, project_path: str = "") -> int | None:
    """
    Find the PID of the Claude process that owns this specific session
    transcript. Uses lsof to find which process has the JSONL file open —
    precise and correct for multi-session scenarios because each session has
    a unique file. Falls back to pgrep+cwd match if lsof returns nothing
    (e.g. file not yet flushed).

    project_path defaults to os.getcwd() — correct when called from within a
    hook process (Claude Code sets cwd to the project for the whole hook
    invocation), but callers from the long-running daemon (which has no
    reason to share cwd with whichever project it's currently evaluating)
    must pass it explicitly.
    """
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

    try:
        resolved_project_path = _norm_path(project_path or os.getcwd())
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
                    if line.startswith("n") and _norm_path(line[1:]) == resolved_project_path:
                        return pid
            except Exception:
                continue
    except Exception:
        pass
    return None


def _find_all_claude_pids_by_project(project_path: str) -> list[int]:
    """Find ALL running 'claude' processes whose cwd matches project_path."""
    pids = []
    resolved_project_path = _norm_path(project_path)
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
                    if line.startswith("n") and _norm_path(line[1:]) == resolved_project_path:
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
    # Ground-truth cross-check before trusting the handover's next_actions
    # blindly — the only one of the three launch paths (this,
    # _open_companion_session, stop.py's relaunch) that didn't already do
    # this. Without it, a launch here just says "execute the Next Action,
    # priority over everything else" with zero verification, even when
    # _infer_direction() itself now detects staleness (see its own
    # docstring/comment, 2026-08-09).
    prompt_arg = ""
    try:
        direction = _infer_direction(project_path)
        if direction["confidence"] >= 0.70:
            prompt_arg = (
                f"Continue work on: {direction['direction']}. Read the handover file for "
                f"the full state.{goal_part} Work autonomously."
            )
    except Exception:
        pass
    if not prompt_arg:
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


QUOTA_NOTIFY_TRIGGER   = 99.0  # only surface the companion/voice once quota reads THIS close to
                               # exhausted — see _execute_quota_trigger's docstring. 90% (the
                               # trigger threshold above) answers "when do we start preparing";
                               # this answers "when is it actually time to interrupt the user".
QUOTA_NOTIFY_POLL_SECS = 60    # how often to re-check the REAL account quota while waiting


def _wait_until_quota_near_exhausted(reset_at_iso: str) -> Optional[float]:
    """
    Silently poll the real account quota (not the stale snapshot the trigger
    fired on) until it's genuinely near exhausted or the reset has already
    passed. The user is never disturbed during this wait — no voice, no
    window — they keep working right up to the real edge of their quota
    instead of getting cut off pre-emptively at the 90% trigger threshold.

    Returns the final confirmed live percentage (fresh, from this function's
    own polling) — or None if it fell through unconfirmed (unparseable reset
    time, reset already passed, or the API never responded). Callers must
    use this return value for anything user-facing, not the stale quota_pct
    the trigger originally fired on: confirmed live 2026-08-12, that stale
    value can be meaningfully behind reality by the time Phase 3 actually
    announces anything, since Phase 1's checkpoint and this function's own
    wait both take real time — "Quota at 97%" was heard several minutes
    after the account had already hit 100% and blocked, because the
    announcement used the number from when the trigger first fired, not a
    fresh read of what this function had just confirmed.

    Fails open: if the reset time is unparseable or the usage API is
    unreachable, falls back to _wait_for_reset's own fallback behavior rather
    than blocking forever on a signal that isn't coming.
    """
    from askr.session.usage_api import get_quota_status

    try:
        reset_at = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
    except Exception:
        _log("could not parse reset time — skipping the near-exhausted wait, falling back")
        return None

    while True:
        now = datetime.now(timezone.utc)
        if now >= reset_at:
            _log("quota reset already passed while waiting to notify — proceeding")
            return None

        status = get_quota_status()
        if status is not None and status.five_hour_pct >= QUOTA_NOTIFY_TRIGGER:
            _log(f"quota now at {status.five_hour_pct:.1f}% (real API) — near exhausted, notifying")
            return status.five_hour_pct

        pct_str = f"{status.five_hour_pct:.1f}%" if status is not None else "unknown"
        remaining = (reset_at - now).total_seconds()
        sleep_for = min(QUOTA_NOTIFY_POLL_SECS, max(remaining, 0))
        if sleep_for <= 0:
            continue
        _log(f"quota={pct_str}, not near exhausted yet — checking again in {int(sleep_for)}s")
        time.sleep(sleep_for)


_NATIVE_RESUME_POLL_SECS  = 20   # how often to re-check the transcript during the watch
_NATIVE_RESUME_GRACE_SECS = 180  # buffer past the real reset for Claude Code's own
                                 # auto-continue to fire and write at least once, before
                                 # askr concludes this session needs a manual nudge


def _watch_for_native_resume(transcript_path: str, reset_at_iso: str, baseline_mtime: float,
                              project_path: str = "", session_id: str = "") -> bool:
    """
    Replaces the 2026-08-11 same-session-resume watch entirely (2026-09-06).
    That version sent Escape to select "wait for reset" and watched for
    activity BEFORE the real reset as a billing-anomaly signal. Retired:
    Claude Code's CLI now natively handles exhausted -> wait -> resume on its
    own ("Usage limit reached ... continuing automatically" -> "Usage limit
    reset ... continuing automatically"), and the native prompt's own
    "esc ... to cancel" wording means Escape now CANCELS that auto-continue
    instead of selecting it — confirmed live, every session askr sent Escape
    to got stuck.

    But native auto-continue isn't universal either — confirmed live the
    same night: some sessions resumed on their own, others sat frozen at the
    limit indefinitely with nothing watching them. So this function never
    touches the terminal; it just watches. It waits until reset_at plus a
    grace buffer (time for the native mechanism to actually fire) and checks
    whether the transcript resumed writing on its own.

    Returns True the moment new activity appears (native auto-continue
    worked — nothing more to do). Returns False if the grace window fully
    elapses with the transcript still frozen (native auto-continue didn't
    happen for this session — the caller should step in with 'cont' itself).
    Fails safe on an unparseable reset time: treats it as "didn't resume,"
    same as the caller's existing pid-unresolved/dead-pid handling.
    """
    try:
        reset_at = datetime.fromisoformat(reset_at_iso.replace("Z", "+00:00"))
    except Exception:
        _log("native-resume watch: could not parse reset time — treating as not-yet-resumed")
        return False

    target = reset_at + timedelta(seconds=_NATIVE_RESUME_GRACE_SECS)

    while True:
        now = datetime.now(timezone.utc)

        try:
            current_mtime = (
                os.path.getmtime(transcript_path)
                if transcript_path and os.path.exists(transcript_path)
                else baseline_mtime
            )
        except Exception:
            current_mtime = baseline_mtime

        if current_mtime > baseline_mtime:
            _log(f"native auto-continue resumed the session on its own — no action needed [{project_path}]")
            return True

        if now >= target:
            _log(f"native-resume watch: grace window elapsed with no activity — "
                 f"falling back to 'cont' [{project_path}]")
            return False

        remaining = (target - now).total_seconds()
        sleep_for = min(_NATIVE_RESUME_POLL_SECS, max(remaining, 0))
        if sleep_for <= 0:
            continue
        time.sleep(sleep_for)


def _get_next_goal(state_dir: str = None) -> str:
    try:
        from askr.state.goals import load_today_goals, load_open_goals
        today = load_today_goals(state_dir)
        if today:
            return today[0]
        return (load_open_goals(state_dir) or [""])[0]
    except Exception:
        return ""


def _write_launch_mode(goal: str = "", parent_session_id: str = None):
    try:
        os.makedirs(os.path.dirname(_LAUNCH_MODE_PATH), exist_ok=True)
        payload = {
            "active": True,
            "goal": goal,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if parent_session_id:
            payload["parent_session_id"] = parent_session_id
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump(payload, f)
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
            why_text = first.get("why", "") if isinstance(first, dict) else ""
            if not action_text or len(action_text) < 10:
                continue
            if why_text == "handover generation failed this session":
                # _build_fallback_handover_dict's degraded placeholder (checkpoint.py)
                # — "Inspect X — verify manually" / "review transcript manually
                # before continuing". Found 2026-07-09: this is >=10 chars, so it
                # passed the check above and was returned as a confident (0.85)
                # direction — silently masking a failed handover generation as if
                # it were a real next step, pointing autonomous sessions at "review
                # manually" instead of keep looking for an actual direction.
                continue

            # Staleness cross-check: has any real (non-askr) commit landed since
            # THIS handover was written? Confirmed 2026-08-09: a session can do
            # real work (commit it) and end without ever crossing a real
            # trigger threshold (context/quota/idle) — its own checkpoint never
            # fires, so canonical handover_<dev>.json stays exactly as the
            # PREVIOUS session left it. curr_hash is the newest handover commit
            # with non-empty next_actions found so far; if commits exist after
            # it, this next_action may already be resolved by work the handover
            # itself has no record of. Trusting it blind sent a fresh autonomous
            # launch to spend several tool calls and minutes re-verifying work
            # someone already finished — burning real tokens confirming a no-op.
            # Older handovers in this same scan would only be MORE stale, so
            # break (not continue) straight to Signal 4's commit-momentum check,
            # which is grounded in the actual most-recent commits regardless of
            # handover staleness.
            try:
                staleness_check = subprocess.run(
                    ["git", "log", "--oneline", f"{curr_hash}..HEAD",
                     "--invert-grep", "--grep=^askr: "],
                    capture_output=True, text=True, timeout=10, cwd=cwd,
                )
                commits_since = [l for l in staleness_check.stdout.splitlines() if l.strip()]
            except Exception:
                commits_since = []
            if commits_since:
                break

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
    #
    # --invert-grep --grep excludes askr's own automated commits ("askr: checkpoint",
    # "askr: idle") from the 10-commit window. Found 2026-07-09: without this, an
    # idle-heavy or research-heavy stretch fills the window with these — their
    # messages never match the conventional-commit scope regex below, and their
    # changed files are always under askr_state/ (already filtered from `paths`
    # below), so they contribute nothing but dilute the sample. A window of 10
    # commits where 6 are automated checkpoints only has 4 real commits to build
    # confidence from — structurally weaker than it should be. git applies
    # --invert-grep during the revision walk, so -10 still yields 10 REAL commits
    # (not 10 total then filtered down).
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--name-only", "-10",
             "--invert-grep", "--grep=^askr: "],
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


def _write_notification(trigger: str, goal: str = "", pct: float = 0.0, handover_ready: bool = False, project_path: str = "", handover_path: str = "", git_pushed: bool = True):
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        pct_str = f"{round(pct * 100)}%" if trigger == "context" else f"{round(pct)}%"
        # git_pushed must reflect the real git_commit_push() outcome, threaded up
        # through create_checkpoint()'s result dict — never claim a push succeeded
        # just because the checkpoint step itself completed. This used to be an
        # unconditional claim regardless of push outcome; checkpoint_error.log
        # has a documented history of pushes silently failing while this still
        # told the user "state saved to git".
        save_clause = "state saved to git" if git_pushed else "checkpoint saved LOCALLY — git push FAILED, see checkpoint_error.log"
        if trigger == "context":
            msg = f"Context at {pct_str} — {save_clause}, full uncompressed memory. Opening new chat."
            voice_msg = f"Context at {pct_str}. {save_clause}. Opening a companion now with full memory."
        else:
            msg = (f"Quota at {pct_str} — {save_clause}, full uncompressed memory. Askr will resume "
                   f"automatically once your quota resets. Keep working here if you have quota left; "
                   f"we won't interrupt again until then.")
            # Voice gets its own short line, not the full popup text read verbatim —
            # but must keep save_clause verbatim: it's the honesty signal tested by
            # WriteNotificationHonestyTests (voice must never claim "state saved to
            # git" when the push actually failed).
            voice_msg = f"Quota at {pct_str}. {save_clause}. Will resume automatically after reset."
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
        _speak(voice_msg, source=f"lifecycle._write_notification.{trigger}", project_path=project_path)
    except Exception:
        pass


def _write_terminal_action_notification(notif_type: str, ancestor_pids: list, project_path: str,
                                         message: str, resume_text: str = ""):
    """
    Same-session rate-limit-resume feature (2026-08-12): the notification
    itself is just the payload — extension.js's own case for notif_type is
    what actually resolves the target Terminal via findTerminalByAncestorPids
    and performs the real action (Escape for 'quota_exhausted_wait', typed
    resume_text for 'quota_resume_cont'). This function only ever writes the
    handoff; it never touches a terminal directly (that's JS-only, no stable
    Python-side API for it).
    """
    try:
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        payload = {
            "type": notif_type,
            "message": message,
            "ancestor_pids": ancestor_pids,
            "project_path": project_path,
            "resume_text": resume_text,
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


def _execute_idle_checkpoint(stats: dict, project_path: str, session_id: str = None):
    """
    Genuine-inactivity trigger — deliberately NOT _execute_quota_trigger(), which is
    built for "quota exhausted, hand off to a fresh session": it labels its
    announcement as a quota message unconditionally for any non-"context"
    trigger (a real bug this idle trigger tripped — "Quota at 41%... waiting
    for reset" spoken for a plain inactivity checkpoint that has nothing to do
    with quota), and it unconditionally auto-launches a brand new claude
    session afterward. Idle inactivity is just a safety-net checkpoint — save
    state, announce it, notify Discord — not a reason to start new autonomous
    work the user never asked for.
    """
    from askr.state.config import load_developer
    from askr.session.safe_pause import is_safe_to_pause
    from askr.session.checkpoint import create_checkpoint

    developer = load_developer()
    _log("trigger=idle — checking safe pause")

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

    _log("safe to pause — creating idle checkpoint")
    from askr.session.monitor import _find_active_jsonl
    transcript_path = _find_active_jsonl(project_path, session_id) or ""
    result = create_checkpoint(trigger_type="idle", developer=developer,
                                transcript_path=transcript_path, state_dir=state_dir)
    _log(f"checkpoint: {result.get('trigger')} at {result.get('timestamp', '')[:19]}")

    idle_minutes = round(IDLE_TRIGGER_SECS / 60)
    if result.get("git_pushed", False):
        _speak(f"Been quiet for {idle_minutes} minutes — state saved to git.",
               source="lifecycle._execute_idle_checkpoint", project_path=project_path)
    else:
        _speak(f"Been quiet for {idle_minutes} minutes — checkpoint saved locally, "
               "but the git push failed. Check checkpoint_error.log.",
               source="lifecycle._execute_idle_checkpoint", project_path=project_path)


def _execute_quota_trigger(stats: dict, project_path: str, session_id: str = None):
    """Thin wrapper around _execute_quota_trigger_impl that keeps caffeinate
    alive for the whole call, including across a session-idle transition
    mid-wait — see _stop_caffeinate()'s docstring for the incident this
    closes."""
    _quota_wait_begin()
    try:
        _execute_quota_trigger_impl(stats, project_path, session_id)
    finally:
        _quota_wait_end()


def _execute_quota_trigger_impl(stats: dict, project_path: str, session_id: str = None):
    """
    Found 2026-07-16: this used to wait up to 10 minutes for a quiet moment
    (TURN_QUIET_GRACE_SECS + MAX_WAIT_SECS, both UX-only — see
    _wait_for_turn_to_finish) before doing ANYTHING, including the checkpoint
    itself, then immediately spoke the "state saved, waiting for reset"
    reassurance right at the 90% trigger point. Two separate problems:

    1. A user who reads-and-replies within 90 seconds (completely normal,
       fast usage) could keep the daemon waiting the full 10 minutes before
       it ever saved anything, while quota kept climbing straight through the
       real 100% wall underneath it — the wait gated pure safety (saving
       state) behind a UX nicety (not popping a window open mid-read) that
       has nothing to do with it.
    2. Speaking the reassurance at 90% cuts the user off ~10% of their
       remaining quota early for no reason — a request already in flight
       when the account crosses the real limit completes normally; only the
       NEXT request gets rejected.

    Fixed with three phases: (1) checkpoint the instant the turn genuinely
    finishes, correctness-only wait, no UX grace; (2) silently poll real
    quota until it's actually near exhausted, user undisturbed the whole
    time; (3) only then surface the companion + voice, and wait for the
    actual reset before launching the companion for real.
    """
    from askr.state.config import load_developer
    from askr.session.safe_pause import is_safe_to_pause
    from askr.session.checkpoint import create_checkpoint

    if not _claude_cli_available():
        _log("WARN: 'claude' not in PATH — skipping trigger (would leave user with nothing)")
        return

    developer = load_developer()
    _log("trigger=quota — checking safe pause")

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

    # Phase 1: checkpoint the instant the turn genuinely finishes. Correctness
    # only — no TURN_QUIET_GRACE_SECS — so this can never be starved by fast
    # typing. is_safe_to_pause() above only checks processes/file-locks, never
    # turn state, so this is still needed to avoid reading a half-finished turn.
    _wait_for_turn_to_finish(project_path, session_id, require_quiet_grace=False)

    state_dir = os.path.join(project_path, "askr_state")
    if not os.path.isdir(state_dir):
        _log(f"WARN: no askr_state/ in {project_path} — skipping checkpoint (run 'askr init' there first)")
        return

    _log("safe to pause — creating checkpoint (silent, no notification yet)")
    from askr.session.monitor import _find_active_jsonl
    transcript_path = _find_active_jsonl(project_path, session_id) or ""
    result = create_checkpoint(trigger_type="quota", developer=developer,
                                transcript_path=transcript_path, state_dir=state_dir)
    _log(f"checkpoint: {result.get('trigger')} at {result.get('timestamp', '')[:19]}")

    # Phase 2: silently wait for quota to actually be near exhausted (or the
    # reset to have already passed). The user keeps working, undisturbed.
    reset_at = stats.get("quota_reset_at")
    fresh_quota_pct = None
    if reset_at:
        fresh_quota_pct = _wait_until_quota_near_exhausted(reset_at)

    # Phase 3: now it's actually time to interrupt.
    next_goal = _get_next_goal(state_dir)
    _write_launch_mode(next_goal, parent_session_id=session_id)
    handover_path = result.get("handover_path", "")
    handover_has_content = bool(handover_path and os.path.exists(handover_path) and
                                os.path.getsize(handover_path) > 200)
    # Confirmed live 2026-08-12: using stats.get("quota_pct") here — the value
    # from whenever the trigger FIRST fired — announced "Quota at 97%" several
    # minutes after the account had already hit 100% and blocked. Phase 1's
    # checkpoint and Phase 2's own wait both take real time; Phase 2 already
    # polls the live API and knows the true current number, so use it instead
    # of the stale snapshot whenever it's available.
    announced_quota_pct = fresh_quota_pct if fresh_quota_pct is not None else stats.get("quota_pct", 0.0)
    _write_notification("quota", next_goal, announced_quota_pct, handover_has_content,
                         project_path, handover_path, git_pushed=result.get("git_pushed", False))

    _verify_native_resume_or_cont(project_path, session_id, transcript_path, reset_at, next_goal, stats)


def _verify_native_resume_or_cont(project_path: str, session_id: str, transcript_path: str,
                                   reset_at: str, next_goal: str, stats: dict):
    """
    Phase 4 (2026-09-06): Claude Code's CLI now natively handles the
    exhausted -> wait -> resume cycle on its own for SOME sessions —
    confirmed live: "Usage limit reached ... continuing automatically at
    <time> ... esc or type to cancel", then "Usage limit reset ...
    continuing automatically". The 2026-08-12 same-session-resume feature
    sent Escape here on a binary analysis showing it equivalent to selecting
    "Stop and wait for limit to reset" — true for that Claude Code version,
    but the CURRENT native prompt's own "esc ... to cancel" wording means
    Escape now CANCELS the native auto-continue instead. Every session askr
    sent Escape to got stuck; every session left untouched resumed on its
    own.

    But native auto-continue isn't universal: confirmed live the same
    night, other sessions that also hit the limit sat frozen indefinitely
    with nothing watching them. So askr no longer sends Escape (never
    interferes with the native path) but does verify it actually happened:
    wait past the real reset plus a grace buffer, then check whether the
    transcript resumed writing on its own. Only if it's still frozen does
    askr step in with 'cont' — the same dead-pid-safe delivery as before,
    falling back to a companion session if the pid can't be resolved or
    has died in the meantime.

    Extracted as its own function (2026-09-06) so it can run per-SESSION
    even when the account-wide quota announcement (checkpoint + voice/
    Discord, above) was already deduped away for this reset window on a
    different session — see _verify_native_resume_for_other_sessions().
    Confirmed live: quota_triggered_windows correctly stops duplicate
    announcements across concurrent sessions sharing one account-wide
    quota, but it was ALSO silently skipping this verify-and-cont step for
    every session but the first, leaving other sessions that hit the same
    limit with nobody watching them at all.
    """
    resumed_natively = False
    same_session_resumed = False
    if reset_at:
        baseline_mtime = None
        try:
            if transcript_path and os.path.exists(transcript_path):
                baseline_mtime = os.path.getmtime(transcript_path)
        except Exception:
            baseline_mtime = None

        # Can't verify native auto-continue without a transcript to watch —
        # don't guess. Skip straight to the companion fallback below, which
        # still waits for the real reset via _wait_for_reset() first.
        if baseline_mtime is not None:
            resumed_natively = _watch_for_native_resume(
                transcript_path, reset_at, baseline_mtime, project_path, session_id or "",
            )

            if not resumed_natively:
                try:
                    pid = _find_session_pid(transcript_path, project_path)
                except Exception:
                    pid = None

                pid_alive = False
                if pid:
                    try:
                        os.kill(pid, 0)
                        pid_alive = True
                    except (ProcessLookupError, PermissionError):
                        pid_alive = False
                    except Exception:
                        pid_alive = True  # unexpected errno — don't assume dead on a shaky signal

                if pid and not pid_alive:
                    _log(f"quota fallback: pid {pid} no longer alive — opening a companion instead of 'cont'")
                elif not pid:
                    _log("quota fallback: pid unresolved — opening a companion instead of 'cont'")

                if pid_alive:
                    ancestor_pids = _get_ancestor_pids(pid)
                    if ancestor_pids:
                        _write_terminal_action_notification(
                            "quota_resume_cont", ancestor_pids, project_path,
                            message="Quota reset — this session didn't auto-continue, so askr is resuming it for you.",
                            resume_text="cont",
                        )
                        _speak("Quota reset. This session didn't auto-continue — resuming it now.",
                               source="lifecycle._execute_quota_trigger.cont_fallback", project_path=project_path,
                               session_id=session_id or "")
                        same_session_resumed = True
                    else:
                        _log("quota fallback: ancestor pids unresolved — opening a companion instead of 'cont'")

    if resumed_natively or same_session_resumed:
        if same_session_resumed:
            _notify_discord_resumed("quota", next_goal)
        try:
            from askr.state.analytics import today_summary
            saved = today_summary().get("total_seconds", 0)
            _write_resumed_marker("quota", saved)
        except Exception:
            pass
        return

    # Fallback: no transcript to watch, pid/ancestor unresolved, the pid died
    # mid-wait, or the grace window elapsed with no native resume and no way
    # to send 'cont' — same last-resort behavior as before this feature
    # existed. _wait_for_reset() no-ops immediately if reset_at already
    # passed (e.g. the watch above already waited it out), so it's always
    # safe to call here regardless of which path led to this point.
    if reset_at:
        _wait_for_reset(reset_at)
    else:
        time.sleep(300)

    _log("starting companion claude session (existing session, if any, left running)")
    launched = _start_claude(project_path, force=True)
    if launched:
        _notify_discord_resumed("quota", next_goal)
        from askr.state.writer import append_event
        append_event("companion_spawned", project_path, parent_session_id=session_id,
                     trigger_type="quota", quota_pct=stats.get("quota_pct"))
    try:
        from askr.state.analytics import today_summary
        saved = today_summary().get("total_seconds", 0)
        _write_resumed_marker("quota", saved)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main daemon loop
# ---------------------------------------------------------------------------

def _pre_kill_update_tools(project_path: str, session_id: str = None):
    """
    Before killing Claude, extract all tools used in the active JSONL and
    persist them to the project's .claude/settings.json allowedTools.
    This ensures the new session inherits full permissions even if SIGKILL
    prevents the Stop hook from running _update_allowed_tools.
    """
    try:
        from askr.session.monitor import _find_active_jsonl
        jsonl = _find_active_jsonl(project_path, session_id)
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
    _pre_kill_update_tools(project_path, session_id)  # sync allowedTools/permissions for the new session

    state_dir = os.path.join(project_path, "askr_state")
    developer = ""
    last_summary = ""
    try:
        from askr.state.config import load_developer
        from askr.session.checkpoint import create_checkpoint
        from askr.session.monitor import _find_active_jsonl
        developer = load_developer()
        if not os.path.isdir(state_dir):
            raise RuntimeError(f"no askr_state/ in {project_path} — run 'askr init' there first")
        # _find_active_jsonl reads the live session's transcript without
        # needing to kill it first — session_id pins the exact file instead
        # of guessing by mtime (wrong whenever 2+ sessions share a project).
        transcript_path = _find_active_jsonl(project_path, session_id) or ""
        checkpoint_result = create_checkpoint(
            trigger_type="context", developer=developer,
            transcript_path=transcript_path, state_dir=state_dir,
        )
        _log(f"checkpoint (companion session): {checkpoint_result.get('trigger')} at {checkpoint_result.get('timestamp','')[:19]}")
        # Read back what the checkpoint just wrote so the toast/terminal can show
        # a TL;DR of the session being companioned — without this, the only way
        # to see what it last said is to switch to it, defeating the point of
        # opening a companion instead of just reading the old one.
        try:
            with open(os.path.join(state_dir, f"handover_{developer}.json")) as f:
                last_summary = (json.load(f).get("discussion_summary") or "").strip()
        except Exception:
            pass
    except Exception as e:
        _log(f"companion checkpoint error: {e}")

    next_goal = _get_next_goal(state_dir)
    _write_launch_mode(next_goal, parent_session_id=session_id)
    allowed_tools = _load_allowed_tools(project_path)

    daemon_prompt = ""
    try:
        direction = _infer_direction(project_path)
        if direction["confidence"] >= 0.70:
            # Only claim a prior session is still live if one actually is — this
            # function is also called when no process was found for the project
            # (see "opening companion session anyway" above), and telling the new
            # session to defer to a phantom other session it should never touch
            # just stalls it for no reason.
            if _find_all_claude_pids_by_project(project_path):
                daemon_prompt = (
                    f"Continue work on: {direction['direction']}. Read the handover file "
                    f"for the full state. Your previous session is still running in another "
                    f"window — pick up from the handover, don't redo work already in flight there."
                )
            else:
                daemon_prompt = (
                    f"Continue work on: {direction['direction']}. Read the handover file "
                    f"for the full state and pick up from the Next Action."
                )
    except Exception:
        pass
    if not daemon_prompt:
        goal_part = f" Work on: {next_goal}." if next_goal else ""
        daemon_prompt = f"Read the handover and start on the Next Action immediately.{goal_part} Work autonomously."

    try:
        # "is ready" implied the companion already existed — it doesn't yet: the
        # extension (or the Terminal.app fallback below, ~20-30s out) opens it
        # asynchronously after this. Say what's actually happening, not the result.
        companion_message = ("Context at 70%+ — opening a fresh companion session now with full, "
                              "uncompressed memory, before Claude's native compaction would compress "
                              "it. Your current session keeps running if you'd like to continue there.")
        if last_summary:
            companion_message += f"\n\nWhat it last did: {last_summary}"
        # Voice gets its own short line, not the full popup text read verbatim —
        # matches pre_compact.py's emergency case, which already does this.
        voice_message = "Context at 70 percent. Opening a companion now with full memory. Your current session keeps running."
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump({
                "type": "context",
                "message": companion_message,
                "last_summary": last_summary,
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": daemon_prompt,
                "shown": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
        _log("wrote notification.json — extension will open a NEW terminal; existing session left running")
    except Exception as e:
        _log(f"companion notification error: {e}")

    # Don't call _start_claude here — force=True bypasses its double-session guard,
    # but that guard exists for the goal-autolaunch path which should still refuse
    # when something's already running. Spawn the terminal directly instead.
    claude_bin  = shutil.which("claude") or "claude"
    tools_flag  = f" --allowedTools {','.join(allowed_tools)}" if allowed_tools else ""
    safe_prompt = daemon_prompt.replace("'", "").replace('"', "").replace("\\", "")
    _spawn_terminal_app_fallback(project_path, claude_bin, tools_flag, safe_prompt, _NOTIFICATION_PATH)
    from askr.state.writer import append_event
    append_event("companion_spawned", project_path, parent_session_id=session_id,
                 trigger_type="context")
    # Speak only once the fallback spawn is actually dispatched, so the announcement
    # never lands before something has genuinely started happening.
    _speak(voice_message, source="lifecycle._open_companion_session",
           project_path=project_path, session_id=session_id or "")


_TURN_STOP_DIR  = os.path.expanduser("~/.config/askr/turn_stops")
_TURN_START_DIR = os.path.expanduser("~/.config/askr/turn_starts")


def _turn_stopped_since(session_id: str, since_ts: float) -> bool:
    """True once stop.py has signaled turn completion for this session_id after since_ts."""
    if not session_id:
        return False
    marker = os.path.join(_TURN_STOP_DIR, f"{session_id}.json")
    return os.path.exists(marker) and os.path.getmtime(marker) >= since_ts


def _turn_marker_still_live(project_path: str, session_id: str) -> bool:
    """
    Backstop for a turn-start marker older than MAX_TURN_ACTIVE_SECS: is this a
    genuinely still-running turn, or a stuck/abandoned one? True only if the
    Claude process for this project is alive AND the session's transcript
    (rewritten by Claude Code itself as it streams text and dispatches tool
    calls — not dependent on any askr hook) has been touched within
    MAX_TURN_ACTIVE_SECS.

    This is not a reintroduction of the bug it backstops: the old check
    flagged ANY turn older than 30 minutes as abandoned, full stop — including
    ones with the transcript growing every few seconds the entire time. This
    only gives up once there's been zero transcript activity for 30 minutes
    despite an open turn — a hard-hung process, not a long one. (A single tool
    call that blocks for more than 30 minutes with no transcript writes in
    between — e.g. one very long shell command — can still misfire this; that
    residual gap is far narrower than the one it replaces.)
    """
    if not _find_all_claude_pids_by_project(project_path):
        return False
    try:
        from askr.session.monitor import _find_active_jsonl
        transcript_path = _find_active_jsonl(project_path, session_id)
        if not transcript_path:
            return False
        return (time.time() - os.path.getmtime(transcript_path)) < MAX_TURN_ACTIVE_SECS
    except Exception:
        return False


def _turn_currently_active(session_id: str, project_path: str = None) -> bool:
    """
    True if the user has submitted a prompt (user_prompt_submit.py's turn-start
    marker) more recently than the last Stop-hook turn-stop marker — i.e. Claude
    is actively working on a reply right now.

    _last_turn_stop() only measures time since the PREVIOUS turn ended, blind to
    whether a new turn has since started. Without this check, idle_secs keeps
    growing through an entire in-progress turn (thinking time before the prompt
    plus however long this turn takes to process), so submitting a question after
    a long gap and then stepping away for even a minute can cross IDLE_TRIGGER_SECS
    while the user is actively present and Claude is still replying — a false
    "been quiet for 10 minutes" with no actual 10 minutes of inactivity.

    project_path is optional but should always be passed when the caller has
    it: without it, an old start marker is treated as abandoned by age alone
    (the pre-2026-08-10 behavior). With it, age alone is only the trigger to
    check liveness (see _turn_marker_still_live), not the verdict itself.
    """
    if not session_id:
        return False
    start_marker = os.path.join(_TURN_START_DIR, f"{session_id}.json")
    if not os.path.exists(start_marker):
        return False
    start_mtime = os.path.getmtime(start_marker)
    if (time.time() - start_mtime) >= MAX_TURN_ACTIVE_SECS:
        if not (project_path and _turn_marker_still_live(project_path, session_id)):
            return False  # no liveness signal to trust an old marker — genuinely abandoned
    stop_marker = os.path.join(_TURN_STOP_DIR, f"{session_id}.json")
    if not os.path.exists(stop_marker):
        return True  # turn started, never stopped yet
    return start_mtime > os.path.getmtime(stop_marker)


def _wait_for_turn_to_finish(project_path: str, session_id: str = None, require_quiet_grace: bool = True) -> bool:
    """
    Block until the current Claude reply finishes AND no new one has started —
    the user must always get a genuinely quiet moment before askr acts on
    their session (opening a companion window, or reading the transcript for
    a checkpoint).

    "Reply finished" is detected via the Stop hook's own completion signal
    (askr/hooks/stop.py writes ~/.config/askr/turn_stops/<session_id>.json when it
    finishes processing a turn) — not JSONL write-silence. The old idle-time
    heuristic false-positived whenever a tool call ran long enough to pause JSONL
    writes for IDLE_THRESHOLD seconds (e.g. a multi-minute git-filter-repo run),
    acting while the original turn was still very much in progress. The Stop
    hook firing is the only authoritative "turn is done" signal.

    Found 2026-07-11: that alone isn't enough. This only watched for the ONE
    turn that was active when the trigger fired — if the user sent a new
    message in the gap between that turn ending and this function actually
    returning (a real possibility: rapid back-and-forth chat), a companion
    would open the instant the new turn started, which looks and feels
    identical to being interrupted mid-reply. Now also requires
    _turn_currently_active() to be false — no turn in flight right now, not
    just "the turn we were originally watching is done."

    Found 2026-07-13: still not enough. Stop fires as soon as the main turn's
    own generation ends, even if that turn dispatched an Agent-tool subagent
    (fork or background agent) whose result is still pending — by every
    turn-marker signal the session looks quiet, but the user is mid-flow,
    waiting on that subagent to report back into the same conversation.
    Popping a companion window open in that gap is exactly as disruptive as
    interrupting a still-generating reply. Now also requires
    has_outstanding_subagent() to be false against the live transcript.

    Found 2026-07-14: still not enough. A plain-text question at the end of a
    reply ("should I do X?") involves no tool call, so Stop fires the instant
    it's generated — _turn_currently_active() goes false immediately, same as
    any other finished turn, even though the user hasn't had a chance to read
    it yet, let alone answer. Now also requires TURN_QUIET_GRACE_SECS of real
    silence since that Stop signal, not just "Stop already fired."

    Found 2026-07-16: TURN_QUIET_GRACE_SECS is a UX nicety (don't yank a
    companion window open while the user's still reading) with no bearing on
    whether it's SAFE to read the transcript — that only needs the turn to
    have genuinely stopped, which _turn_currently_active() already tells you
    instantly. But the quota trigger's checkpoint used to sit behind this same
    90s/600s wait, meaning a user who reads-and-replies within 90 seconds
    (completely normal, fast usage) could keep quota climbing straight through
    the real 100% wall before anything was ever saved — the UX-only wait was
    gating pure safety. require_quiet_grace=False skips straight to the
    correctness-only condition (turn stopped, no outstanding subagent) with no
    grace period, for callers where disturbing the user was never the concern
    — just reading a transcript that's actually finished generating.

    Returns True if a live session was found and waited on, False if no live
    process was detected for this project (nothing to wait for).
    """
    if not _find_all_claude_pids_by_project(project_path):
        _log("claude process not found for this project — nothing to wait for")
        return False

    from askr.session.monitor import _find_active_jsonl
    from askr.session.checkpoint import has_outstanding_subagent

    POLL          = 5    # polling interval (seconds)
    MAX_WAIT_SECS = 600  # only forces past the grace-period/outstanding-subagent niceties (a user
                          # who never goes quiet between messages) — never overrides a turn that's
                          # still genuinely active. Found 2026-08-10: this used to force the
                          # companion open unconditionally at 600s, which fired mid-reply during a
                          # single turn that ran past 10 minutes straight (confirmed in production —
                          # zero Stop signals the entire wait). _turn_currently_active()'s own
                          # PID-liveness check (see _turn_marker_still_live) is what actually decides
                          # when a genuinely active turn ends; this cap only ever short-circuits the
                          # UX-only waiting once the turn itself is already done.

    if require_quiet_grace:
        _log("waiting for a genuinely quiet moment (Stop hook fired, no new turn, no outstanding "
             f"subagent, {TURN_QUIET_GRACE_SECS}s of silence since)...")
    else:
        _log("waiting for the current turn to genuinely finish (no UX grace — correctness only)...")

    wait_start = time.time()
    waited = 0

    while True:
        time.sleep(POLL)
        waited += POLL

        if not _find_all_claude_pids_by_project(project_path):
            _log("claude session ended while waiting")
            break

        turn_active = _turn_currently_active(session_id, project_path)
        _, stop_idle_secs = _last_turn_stop(session_id)
        turn_genuinely_done = (
            _turn_stopped_since(session_id, wait_start) and not turn_active
            and not has_outstanding_subagent(_find_active_jsonl(project_path, session_id) or "")
        )
        if require_quiet_grace:
            turn_genuinely_done = (
                turn_genuinely_done and stop_idle_secs is not None
                and stop_idle_secs >= TURN_QUIET_GRACE_SECS
            )
        if turn_genuinely_done:
            _log("Stop hook fired, no new turn active, no outstanding subagent"
                 + (f", {stop_idle_secs:.0f}s quiet" if require_quiet_grace else "")
                 + " — reply finished")
            break

        if waited >= MAX_WAIT_SECS and not turn_active:
            _log(f"WARN: waited {MAX_WAIT_SECS}s without a quiet moment (turn itself already "
                 "finished) — proceeding anyway")
            break
        elif waited >= MAX_WAIT_SECS and waited % 300 == 0:
            _log(f"turn still genuinely active after {waited}s — continuing to wait, "
                 "not forcing through a live reply")

    return True


def _open_companion_session_for_trigger(project_path: str, session_id: str = None) -> bool:
    """
    Context trigger fired. Wait for the current Claude reply to finish before
    opening the companion session — the user must always get their complete reply
    before a second window appears.

    Returns True if a live session was found (full cooldown applies), False if
    no live process was detected (short retry).
    """
    found = _wait_for_turn_to_finish(project_path, session_id)
    _open_companion_session(project_path, session_id)
    return found


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


def _prune_companioned_sessions(companioned_sessions: set) -> set:
    """
    Drop only entries with POSITIVE proof their session has exited —
    registry.is_session_confirmed_dead. Never prune on "we don't know."

    Three incidents, same underlying lesson, each fixing the previous fix's
    blind spot:

    2026-07-09: a per-turn Stop-hook cleanup discarded a session's entry
    here on every Stop firing — but Stop fires after every assistant turn,
    not just at session end, so the "already got a companion" flag was wiped
    after a session's very first reply. Fixed with liveness-based pruning
    against _read_all_stats' SESSION_STALE_SECS (10 min) window.

    2026-07-11 (first): that pruned on stats staleness, which lapses
    whenever the Mac sleeps or a window sits idle, not just when a session
    ends. Waking the machine after any longer nap re-fired a companion for
    a window never closed. Fixed by checking the session registry's
    recorded PID instead.

    2026-07-11 (second): the registry itself isn't reliable — registration
    is wrapped in a bare except and silently no-ops for sessions that
    started before it existed or during any hook gap. Of the dozens of
    distinct sessions active in one day, exactly one had a registry entry.
    Treating "no entry" as "dead" pruned nearly every companioned session
    on the very next poll cycle regardless of actual liveness. Fixed by
    requiring POSITIVE proof of death (is_session_confirmed_dead) — no
    entry, or no confirmable PID, now means "leave it alone," not "gone."
    """
    from askr.utils.retry import import_retry
    try:
        def _import_check():
            from askr.session.registry import is_session_confirmed_dead
            return is_session_confirmed_dead
        is_session_confirmed_dead = import_retry(_import_check)
    except ImportError:
        # Same fail-safe rule as everywhere else in this function: if we
        # can't even confirm the check itself, don't prune this cycle.
        return companioned_sessions
    stale = {sid for sid in companioned_sessions if is_session_confirmed_dead(sid)}
    if not stale:
        return companioned_sessions
    pruned = companioned_sessions - stale
    _save_companioned_sessions(pruned)
    return pruned


def _load_quota_warned_windows() -> set:
    """quota_reset_at timestamps already given the QUOTA_WARNING_TRIGGER heads-up.

    Keyed by the account's actual 5h reset window, not session_id — quota is
    account-wide, so a new chat session doesn't mean a new quota window. Keying
    by session_id let the warning re-fire every time a session (or a companion
    askr itself opens) restarted mid-window, even though nothing about the real
    quota had changed since the last warning."""
    try:
        with open(_QUOTA_WARNED_SESSIONS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_quota_warned_windows(windows: set):
    try:
        os.makedirs(os.path.dirname(_QUOTA_WARNED_SESSIONS_PATH), exist_ok=True)
        with open(_QUOTA_WARNED_SESSIONS_PATH, "w") as f:
            json.dump(list(windows), f)
    except Exception as e:
        _log(f"WARN: failed to persist quota-warned sessions: {e}")


def _load_quota_triggered_windows() -> set:
    """quota_reset_at timestamps that already had the 90% hard trigger fired.

    Without this, the per-trigger-type cooldown is the only gate on the quota
    branch below — but quota stays >=90% for the whole 5h window until reset,
    so every poll cycle after cooldown expires spawns another
    _execute_quota_trigger thread, each of which re-announces the same
    'Quota at X% — state saved' line and re-checkpoints, for as long as the
    wait lasts. Keyed by the account's real reset window, same as
    _load_quota_warned_windows, not by session_id."""
    try:
        with open(_QUOTA_TRIGGERED_WINDOWS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_quota_triggered_windows(windows: set):
    try:
        os.makedirs(os.path.dirname(_QUOTA_TRIGGERED_WINDOWS_PATH), exist_ok=True)
        with open(_QUOTA_TRIGGERED_WINDOWS_PATH, "w") as f:
            json.dump(list(windows), f)
    except Exception as e:
        _log(f"WARN: failed to persist quota-triggered windows: {e}")


def _load_quota_resume_verified() -> set:
    """"session_id::reset_at" strings already run through Phase 4's native-resume
    verification for the current account-wide window — see
    _QUOTA_RESUME_VERIFIED_PATH for why this is separate from the
    announcement-only dedup above."""
    try:
        with open(_QUOTA_RESUME_VERIFIED_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _save_quota_resume_verified(verified: set):
    try:
        os.makedirs(os.path.dirname(_QUOTA_RESUME_VERIFIED_PATH), exist_ok=True)
        with open(_QUOTA_RESUME_VERIFIED_PATH, "w") as f:
            json.dump(list(verified), f)
    except Exception as e:
        _log(f"WARN: failed to persist quota-resume-verified sessions: {e}")


def _verify_native_resume_for_other_session(project_path: str, session_id: str, stats: dict):
    """
    Runs Phase 4 (native-resume verification + 'cont' fallback) for a
    session whose account-wide quota window was already announced by a
    DIFFERENT session — see _QUOTA_RESUME_VERIFIED_PATH's docstring for why
    that announcement dedup must not also skip this. Deliberately skips
    Phase 1-3 entirely (no checkpoint, no duplicate voice/Discord
    announcement) — those already happened once for this window; this is
    purely "does THIS session's own terminal need a 'cont' too."
    """
    reset_at = stats.get("quota_reset_at")
    if not reset_at:
        return

    state_dir = os.path.join(project_path, "askr_state")
    if not os.path.isdir(state_dir):
        return

    from askr.session.monitor import _find_active_jsonl
    transcript_path = _find_active_jsonl(project_path, session_id) or ""
    next_goal = _get_next_goal(state_dir)
    _verify_native_resume_or_cont(project_path, session_id, transcript_path, reset_at, next_goal, stats)


_RESET_WINDOW_TOLERANCE_SECS = 300  # far below the 5h gap between real windows, comfortably
                                     # above the observed cross-session jitter (below)


def _reset_window_already_triggered(reset_at: str, quota_triggered_windows: set) -> bool:
    """
    Confirmed live 2026-08-11/12: two DIFFERENT sessions on the exact same
    5-hour account window independently polled the usage API and recorded
    quota_reset_at as "...T17:29:59.666245+00:00" and "...T17:30:00.122998+00:00"
    — the same logical reset moment, but straddling a full minute boundary.
    quota_triggered_windows used to be checked via exact string membership
    (`reset_at in quota_triggered_windows`), so every session with its own
    independently-polled reset_at string defeated the dedup entirely — each
    one fired its own Trigger B, ran its own Phase 1-3, and spoke its own
    "Quota at X%" announcement for what was really one account-wide
    exhaustion event. This is why a real 100%-exhaustion could be followed by
    a SEPARATE "97%" announcement several minutes later — not one delayed
    announcement, but two independently-fired ones, each reading whatever
    quota_pct its own stats file happened to have at trigger time.

    Tolerance-based instead of exact-match: treats reset_at as "already
    triggered" if any stored entry is within _RESET_WINDOW_TOLERANCE_SECS —
    far more than the observed sub-minute jitter, far less than the 5h gap
    between genuinely different windows, so this can't merge two real windows.
    """
    try:
        target = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
    except Exception:
        return reset_at in quota_triggered_windows  # fail back to exact match on bad input

    for existing in quota_triggered_windows:
        try:
            existing_dt = datetime.fromisoformat(existing.replace("Z", "+00:00"))
        except Exception:
            continue
        if abs((target - existing_dt).total_seconds()) <= _RESET_WINDOW_TOLERANCE_SECS:
            return True
    return False


def _load_idle_triggered() -> dict:
    try:
        with open(_IDLE_TRIGGERED_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_idle_triggered(triggered: dict):
    try:
        os.makedirs(os.path.dirname(_IDLE_TRIGGERED_PATH), exist_ok=True)
        with open(_IDLE_TRIGGERED_PATH, "w") as f:
            json.dump(triggered, f)
    except Exception as e:
        _log(f"WARN: failed to persist idle-triggered state: {e}")


def _load_session_first_seen() -> dict:
    try:
        with open(_SESSION_FIRST_SEEN_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_session_first_seen(first_seen: dict):
    try:
        os.makedirs(os.path.dirname(_SESSION_FIRST_SEEN_PATH), exist_ok=True)
        with open(_SESSION_FIRST_SEEN_PATH, "w") as f:
            json.dump(first_seen, f)
    except Exception as e:
        _log(f"WARN: failed to persist session-first-seen state: {e}")


def _prune_session_first_seen(first_seen: dict) -> dict:
    """Drop entries older than a day — this dict only exists to answer "was
    this session observed within the last ACTIVITY_GRACE_SECS (60s)", so
    nothing about it needs long-term accuracy the way companioned_sessions'
    liveness-proof pruning does. Purely to keep the file from growing forever
    across days of daemon uptime."""
    cutoff = time.time() - 86400
    return {sid: ts for sid, ts in first_seen.items() if ts >= cutoff}


def _load_session_parent() -> dict:
    try:
        with open(_SESSION_PARENT_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_session_parent(session_parent: dict):
    try:
        os.makedirs(os.path.dirname(_SESSION_PARENT_PATH), exist_ok=True)
        with open(_SESSION_PARENT_PATH, "w") as f:
            json.dump(session_parent, f)
    except Exception as e:
        _log(f"WARN: failed to persist session-parent state: {e}")


def _prune_session_parent(session_parent: dict, session_first_seen: dict) -> dict:
    """Drop any entry whose session_id has already aged out of
    session_first_seen (1 day) — same lifetime, no separate timestamp needed."""
    return {sid: pid for sid, pid in session_parent.items() if sid in session_first_seen}


def _prune_idle_triggered(idle_triggered: dict) -> dict:
    """Drop entries whose dedup was recorded more than a day ago. Purely to
    keep idle_triggered.json from growing forever now that it's keyed per
    (project_path, session_id) — see the 2026-07-24 fix note on Trigger C
    below for why the key changed.

    Found 2026-07-25: the first cut of this pruned on the AGE OF THE STORED
    turn_stop_ts, not on when the dedup entry itself was recorded. But
    turn_stop_ts is deliberately old for exactly the long-abandoned sessions
    Trigger C exists to catch (it's gated on idle_secs >= IDLE_TRIGGER_SECS,
    so it's never fresh) — a leaps session idle 14 days got its brand-new
    dedup entry pruned on the very next poll cycle (~15s later) because a
    14-day-old timestamp reads as "older than a day," undoing the guard
    immediately and reintroducing the exact re-fire-every-poll bug the
    (project_path, session_id) key was meant to fix. Each entry now also
    carries recorded_at (set when Trigger C actually fires) so pruning
    tracks dedup age instead of idle age. Legacy entries from before this
    change are bare ISO strings, not dicts — dropped harmlessly here; if
    that session is still genuinely idle, Trigger C just re-records it
    correctly on the next cycle."""
    cutoff = time.time() - 86400
    return {
        key: entry for key, entry in idle_triggered.items()
        if isinstance(entry, dict) and entry.get("recorded_at", 0) >= cutoff
    }


def _last_turn_stop(session_id: str):
    """(iso_mtime_str, seconds_ago) from this session's turn-stop marker
    (written by stop.py's _signal_turn_stopped on every turn), or (None, None)
    if this session has never stopped a turn yet — never treat "no marker" as
    "idle forever", that would fire on a session's very first turn."""
    if not session_id:
        return None, None
    marker = os.path.join(_TURN_STOP_DIR, f"{session_id}.json")
    if not os.path.exists(marker):
        return None, None
    try:
        mtime = os.path.getmtime(marker)
        return datetime.fromtimestamp(mtime, timezone.utc).isoformat(), (time.time() - mtime)
    except Exception:
        return None, None


def _speak(message: str, source: str = "", project_path: str = "", session_id: str = ""):
    try:
        from askr.clients.voice import announce
        announce(message, context={"source": source, "project_path": project_path, "session_id": session_id})
    except Exception:
        pass


def _evaluate_session_triggers(
    stats: dict,
    session_first_seen: dict,
    quota_warned_windows: set,
    companioned_sessions: set,
    last_trigger_at: dict,
    quota_triggered_windows: set,
    idle_triggered: dict,
    session_parent: dict = None,
    quota_resume_verified: set = None,
) -> None:
    """
    Evaluate all three triggers (context, quota, idle) for one session's stats
    entry. Mutates the passed-in state containers in place and persists them
    via the existing _save_* helpers — exactly what the inline code in
    run_daemon() used to do, just extracted so it's actually unit-testable
    (nothing inside an infinite `while True:` loop can be exercised directly).

    Found 2026-07-16: previously a single if/elif/elif chain, so the FIRST
    matching branch won and every branch after it was skipped for the whole
    cycle. Context trips at 60% — far below quota's 90% or any real idle gap
    — so in a real working session context fires first, marks
    already_companioned, and that first branch matches forever afterward
    (ctx_pct essentially never drops back below CONTEXT_TRIGGER once it's
    climbed). Quota and idle became structurally unreachable for that session
    for as long as it kept running — confirmed in production: a session sat
    "already has a companion open" for 24+ hours while quota climbed from 57%
    to 89% underneath it, Trigger B never once evaluated. Each trigger type
    now gets its own independent if-block and its own cooldown key, so
    tripping one can never block the others from firing on a later cycle.
    """
    project_path = stats.get("project_path")
    if not project_path:
        # Same bug class as the sibling-repo leak fixed 2026-07-02 in
        # get_state_dir(): falling back to a single globally-stored path
        # here could apply a trigger/checkpoint to the WRONG project when
        # multiple projects are active at once. Every writer of a stats
        # file populates project_path, so this should never actually hit —
        # skip rather than guess if it somehow does.
        _log("WARN: stats entry missing project_path — skipping rather than "
             "guessing which project it belongs to")
        return
    ctx_pct   = stats.get("context_pct", 0)
    ctx_label = stats.get("context_label", "ok")
    quota_pct = stats.get("quota_pct")
    reset_at  = stats.get("quota_reset_at", "")

    # Cache-miss population only — instant no-op on every cycle once a
    # model is cached. On a genuine miss this makes one live Models API
    # call (OAuth, fails open) so the *next* hook-computed context_pct
    # for this session uses the model's real window instead of the
    # conservative default. See askr/session/model_windows.py.
    model = stats.get("model")
    if model:
        from askr.session.model_windows import ensure_cached
        ensure_cached(model)

    session_id = stats.get("session_id")
    already_companioned = bool(session_id) and session_id in companioned_sessions
    turn_stop_ts, idle_secs = _last_turn_stop(session_id)
    if session_parent is None:
        session_parent = {}
    if quota_resume_verified is None:
        quota_resume_verified = set()

    # Grace period: give a newly-observed session a moment before evaluating
    # any trigger against it. Quota is account-wide, so a brand-new chat can
    # otherwise inherit an already-high % from prior usage and get interrupted
    # (or hear the 75% warning) before the user has even sent a first message.
    if session_id:
        is_new_to_this_dict = session_id not in session_first_seen
        first_seen = session_first_seen.setdefault(session_id, time.time())
        if is_new_to_this_dict:
            # Disk-backed so a source-watch self-restart (see run_daemon's
            # own "source files updated — exiting for launchd restart") never
            # resets this session's clock back to zero. Confirmed in
            # production 2026-07-23: restarts recurring faster than
            # ACTIVITY_GRACE_SECS (60s) during active development kept
            # re-seeding this as an in-memory-only dict, so a session's
            # grace period never actually expired and its context/quota/idle
            # triggers were skipped indefinitely — including, most visibly,
            # never opening a companion no matter how high context climbed.
            _save_session_first_seen(session_first_seen)
            # First time we've seen this session_id at all: if launch_mode.json
            # currently names a parent (written moments earlier by this same
            # daemon process at companion-spawn time — see _write_launch_mode),
            # record the lineage now, while it's still fresh. See
            # _SESSION_PARENT_PATH docstring for the known best-effort race.
            if session_id not in session_parent:
                try:
                    with open(_LAUNCH_MODE_PATH) as f:
                        parent = json.load(f).get("parent_session_id")
                    if parent:
                        session_parent[session_id] = parent
                        _save_session_parent(session_parent)
                except Exception:
                    pass
        if (time.time() - first_seen) < ACTIVITY_GRACE_SECS:
            _log(f"activity grace period — skipping trigger checks for new session "
                 f"{session_id[:8]} [{project_path}]")
            return

    # Pre-emptive heads-up, independent of the trigger/cooldown state below —
    # it doesn't checkpoint or open anything, just speaks once per quota window
    # (keyed by the account's real reset time, not session_id — the 5h window
    # doesn't reset just because a new chat session started).
    if (reset_at and quota_pct is not None
            and QUOTA_WARNING_TRIGGER <= quota_pct < QUOTA_TRIGGER
            and reset_at not in quota_warned_windows):
        _log(f"quota warning: {quota_pct:.1f}% (real API) [{project_path}] resets={reset_at}")
        quota_warned_windows.add(reset_at)
        _save_quota_warned_windows(quota_warned_windows)
        _speak(f"Quota at {round(quota_pct)} percent. Consider wrapping up soon.",
               source="lifecycle.quota_warning_headsup", project_path=project_path,
               session_id=session_id or "")

    ctx_cooldown_key   = f"{project_path}::context"
    quota_cooldown_key = f"{project_path}::quota"
    logged_something = False

    # --- Context (Trigger A) ---
    if already_companioned and ctx_pct >= CONTEXT_TRIGGER:
        # This exact session already got a companion. Since we never kill
        # it, it stays above CONTEXT_TRIGGER for as long as it keeps
        # running — the per-project cooldown alone would just expire and
        # re-fire against this same session every 300s forever, stacking
        # up an unbounded number of companion terminals. One companion
        # per session, period, until that session actually ends.
        _log(f"session {session_id[:8]} already has a companion open — not spawning another (ctx={ctx_pct:.1%})")
        logged_something = True
    elif ctx_pct >= CONTEXT_TRIGGER and (time.time() - last_trigger_at.get(ctx_cooldown_key, 0.0)) < TRIGGER_COOLDOWN:
        remaining = int(TRIGGER_COOLDOWN - (time.time() - last_trigger_at.get(ctx_cooldown_key, 0.0)))
        _log(f"context cooldown: {remaining}s remaining — ctx={ctx_pct:.1%} project={project_path}")
        logged_something = True
    elif ctx_pct >= CONTEXT_TRIGGER:
        _log(f"Trigger A: context={ctx_pct:.1%} — opening companion session [{project_path}] (existing session left running)")
        logged_something = True
        from askr.state.writer import append_event
        append_event("trigger_fired", project_path, session_id=session_id,
                     parent_session_id=session_parent.get(session_id), trigger_type="context",
                     context_pct=ctx_pct, context_tokens=stats.get("context_tokens"),
                     quota_pct=quota_pct)
        if session_id:
            companioned_sessions.add(session_id)
            _save_companioned_sessions(companioned_sessions)
        # _open_companion_session_for_trigger can block for up to 600s waiting
        # for the current turn to finish — run it off the poll-loop thread so
        # other projects keep getting monitored while this one waits.
        found = bool(_find_all_claude_pids_by_project(project_path))
        threading.Thread(
            target=_open_companion_session_for_trigger,
            args=(project_path, session_id),
            daemon=True,
        ).start()
        if found:
            # Full cooldown — companion opened alongside a live session
            last_trigger_at[ctx_cooldown_key] = time.time()
        else:
            # No live claude process — short cooldown so we retry quickly
            # rather than waiting the full 5 minutes
            last_trigger_at[ctx_cooldown_key] = time.time() - TRIGGER_COOLDOWN + TRIGGER_MISS_COOLDOWN
            _log(f"no live session found — retry in {TRIGGER_MISS_COOLDOWN}s")
        _save_trigger_state(last_trigger_at)

    # --- Quota (Trigger B) — independent of context's state above ---
    if (quota_pct is not None and quota_pct >= QUOTA_TRIGGER and reset_at
            and _reset_window_already_triggered(reset_at, quota_triggered_windows)):
        # Already fired the hard trigger for this reset window — quota stays
        # >=90% for the whole 5h window, so without this the per-project
        # cooldown alone would spawn a fresh _execute_quota_trigger thread — and
        # re-speak the same "Quota at X%" line — every 5 minutes for as long
        # as the wait lasts.
        _log(f"quota trigger already fired for this window — not re-announcing (quota={quota_pct:.1f}%) [{project_path}]")
        logged_something = True

        # Found 2026-09-06: this dedup correctly stops duplicate voice/Discord
        # announcements across concurrent sessions sharing one account-wide
        # quota window, but it was ALSO silently skipping the native-resume
        # verification (Phase 4) for every session except whichever fired the
        # trigger first — confirmed live, a second session sharing the window
        # sat frozen at its limit with nobody watching it, needing a manual
        # 'cont'. Each session is a separate terminal and needs its own
        # check, keyed here per (session_id, reset_at) so it only runs once
        # per session per window, independent of the announcement dedup above.
        if session_id:
            resume_key = f"{session_id}::{reset_at}"
            if resume_key not in quota_resume_verified:
                quota_resume_verified.add(resume_key)
                _save_quota_resume_verified(quota_resume_verified)
                threading.Thread(
                    target=_verify_native_resume_for_other_session,
                    args=(project_path, session_id, stats),
                    daemon=True,
                ).start()
    elif quota_pct is not None and quota_pct >= QUOTA_TRIGGER and not reset_at:
        # Real bug found 2026-07-09: this branch used to fire unconditionally
        # on quota_pct alone, while the dedup case above can only engage
        # when reset_at is truthy. A fresh per-session stats file (new session_id,
        # or a companion askr itself just opened) starts with reset_at=None until
        # its first successful usage-API refresh in post_tool_use.py — during that
        # window quota_pct can still read a stale-but-real 90%+ from ANOTHER
        # source, so this condition was true with nothing to dedup on, and kept
        # re-firing (and re-speaking "Quota at X%") every poll cycle for as long
        # as reset_at stayed empty. quota_triggered_windows.json was confirmed
        # empty in production despite repeated announcements — proof the guard
        # never actually engaged. Skip and retry next cycle instead: without a
        # real reset_at we can't safely promise "waiting for reset" anyway.
        _log(f"quota={quota_pct:.1f}% >= trigger but reset_at not yet known — "
             f"skipping this cycle, will retry [{project_path}]")
        logged_something = True
    elif (quota_pct is not None and quota_pct >= QUOTA_TRIGGER
            and (time.time() - last_trigger_at.get(quota_cooldown_key, 0.0)) >= TRIGGER_COOLDOWN):
        _log(f"Trigger B: quota={quota_pct:.1f}% (real API) [{project_path}]")
        logged_something = True
        from askr.state.writer import append_event
        append_event("trigger_fired", project_path, session_id=session_id,
                     parent_session_id=session_parent.get(session_id), trigger_type="quota",
                     context_pct=ctx_pct, context_tokens=stats.get("context_tokens"),
                     quota_pct=quota_pct)
        quota_triggered_windows.add(reset_at)
        _save_quota_triggered_windows(quota_triggered_windows)
        # _execute_quota_trigger can block for hours (near-exhausted poll, then
        # _wait_for_reset) — run it off the poll-loop thread so other open
        # projects don't go unmonitored for the whole quota window (this was
        # the root cause of triggers/warnings stacking up and firing all at
        # once when the loop finally woke up).
        threading.Thread(
            target=_execute_quota_trigger,
            args=(stats, project_path, session_id),
            daemon=True,
        ).start()
        last_trigger_at[quota_cooldown_key] = time.time()
        _save_trigger_state(last_trigger_at)

    # --- Idle (Trigger C) — independent of context's and quota's state above ---
    # Keyed by (project_path, session_id), not project_path alone: found
    # 2026-07-24, multiple concurrent/abandoned sessions left open against the
    # same project each have their OWN turn_stop_ts. With a project_path-only
    # key, evaluating session A (fires, stores tsA) then session B (different
    # tsB != tsA, fires again, overwrites to tsB) in the same poll cycle left
    # exactly one winner remembered — the next cycle re-evaluates whichever
    # session lost that race, sees its own tsA no longer matches the stored
    # tsB, and re-fires. Two long-idle sessions on one project were enough to
    # thrash forever, re-announcing "been quiet for 10 minutes" every poll.
    idle_key = f"{project_path}::{session_id}"
    prev_entry = idle_triggered.get(idle_key)
    prev_ts = prev_entry.get("turn_stop_ts") if isinstance(prev_entry, dict) else prev_entry
    if (turn_stop_ts is not None and idle_secs >= IDLE_TRIGGER_SECS
            and prev_ts != turn_stop_ts
            and not _turn_currently_active(session_id, project_path)):
        _log(f"Trigger C: idle {idle_secs:.0f}s >= {IDLE_TRIGGER_SECS}s [{project_path}] session={session_id[:8] if session_id else '?'}")
        logged_something = True
        from askr.state.writer import append_event
        append_event("trigger_fired", project_path, session_id=session_id,
                     parent_session_id=session_parent.get(session_id), trigger_type="idle",
                     context_pct=ctx_pct, context_tokens=stats.get("context_tokens"),
                     quota_pct=quota_pct)
        # Stores recorded_at (when WE fired) alongside turn_stop_ts (the
        # session's own, deliberately-old idle marker) so pruning can key off
        # dedup age instead of idle age — see _prune_idle_triggered.
        idle_triggered[idle_key] = {"turn_stop_ts": turn_stop_ts, "recorded_at": time.time()}
        _save_idle_triggered(idle_triggered)
        # _execute_idle_checkpoint(), not _execute_quota_trigger() — the latter
        # is built for "quota exhausted, hand off to a fresh session" and
        # unconditionally auto-launches a new claude session, which genuine
        # inactivity should never do on its own. Off-thread, same as
        # Trigger B, so other open projects don't go unmonitored.
        threading.Thread(
            target=_execute_idle_checkpoint,
            args=(stats, project_path, session_id),
            daemon=True,
        ).start()
        last_trigger_at[project_path] = time.time()
        _save_trigger_state(last_trigger_at)

    if not logged_something:
        q_str = f"quota={quota_pct:.1f}%" if quota_pct is not None else "quota=?"
        _log(f"ok: ctx={ctx_pct:.1%} [{ctx_label}] {q_str} project={project_path}")


_STALE_HIGH_QUOTA_MAX_AGE_SECS = 7200  # 2h — generous enough to catch a session frozen mid-block,
                                        # without matching genuinely abandoned sessions from days ago
_STALE_HIGH_QUOTA_THRESHOLD    = 75.0  # matches QUOTA_WARNING_TRIGGER — "was clearly approaching
                                        # exhaustion when its stats file stopped updating"


def _read_stale_high_quota_stats() -> list:
    """
    Confirmed live 2026-08-12: a session's stats file can freeze at a
    below-trigger quota_pct (observed: 84.0%, bit-for-bit identical across
    every 15s poll for 5+ minutes straight) while the REAL account keeps
    climbing past 90% and blocks entirely. quota_pct only ever refreshes via
    PostToolUse, which needs a SUCCESSFUL tool call to fire — once the
    account is genuinely exhausted, no more successful calls happen to
    refresh it, so the file just stops updating at whatever it last
    recorded. _read_all_stats()'s SESSION_STALE_SECS (10 min) freshness
    filter EXCLUDES exactly these files — the ones that most need checking,
    because they stopped updating precisely because they're blocked.

    This is the complementary read: stats whose last quota_pct was already
    high but have since gone stale, bounded to a few hours so it can't match
    sessions abandoned days ago.
    """
    try:
        if not os.path.isdir(_STATS_DIR):
            return []
        now = time.time()
        results = []
        for f in os.listdir(_STATS_DIR):
            if not f.endswith(".json"):
                continue
            path = os.path.join(_STATS_DIR, f)
            try:
                age = now - os.path.getmtime(path)
            except Exception:
                continue
            if age < SESSION_STALE_SECS or age >= _STALE_HIGH_QUOTA_MAX_AGE_SECS:
                continue  # either already covered by _read_all_stats, or too old to trust
            try:
                with open(path) as fp:
                    data = json.load(fp)
            except Exception:
                continue
            if (data.get("quota_pct") or 0) >= _STALE_HIGH_QUOTA_THRESHOLD:
                results.append(data)
        return results
    except Exception:
        return []


_INDEPENDENT_QUOTA_POLL_SECS = 60  # matches QUOTA_NOTIFY_POLL_SECS's own cadence


def _poll_independent_quota_and_fire(last_poll_ts: float, quota_triggered_windows: set,
                                      session_parent: dict) -> float:
    """
    Runs on EVERY daemon loop iteration, active or idle — the entire point
    is that this must not depend on _session_is_active() or any single
    per-project stats file being fresh, both of which gate the normal
    per-project trigger check in _evaluate_session_triggers(). Quota is
    account-wide, not per-project, so one direct poll here covers every
    project regardless of which one (if any) currently looks "active."

    Closes a real gap confirmed live: a per-project stats file frozen below
    QUOTA_TRIGGER can never cross it on its own once tool calls stop — this
    polls the true account state directly and, when genuinely at or above
    QUOTA_TRIGGER, fires _execute_quota_trigger for every project whose
    stats (fresh, or recently-stale-but-was-high — see
    _read_stale_high_quota_stats) suggest it's an affected session.

    Returns the new last_poll_ts — unchanged if this cycle didn't poll
    (throttled to _INDEPENDENT_QUOTA_POLL_SECS, same cadence the rest of the
    quota machinery already uses) or if the window was already handled.
    """
    now = time.time()
    if now - last_poll_ts < _INDEPENDENT_QUOTA_POLL_SECS:
        return last_poll_ts

    try:
        from askr.session.usage_api import get_quota_status
        status = get_quota_status()
    except Exception:
        status = None
    if status is None or status.five_hour_pct < QUOTA_TRIGGER:
        return now

    reset_at = status.five_hour_reset.isoformat()
    if _reset_window_already_triggered(reset_at, quota_triggered_windows):
        return now

    candidates = _read_all_stats() + _read_stale_high_quota_stats()
    seen_projects = set()
    fired_any = False
    for stats in candidates:
        project_path = stats.get("project_path")
        if not project_path or project_path in seen_projects:
            continue
        seen_projects.add(project_path)
        session_id = stats.get("session_id")
        _log(f"Trigger B (independent poll): quota={status.five_hour_pct:.1f}% (real API) [{project_path}]")
        try:
            from askr.state.writer import append_event
            append_event("trigger_fired", project_path, session_id=session_id,
                         parent_session_id=session_parent.get(session_id), trigger_type="quota",
                         context_pct=stats.get("context_pct"), context_tokens=stats.get("context_tokens"),
                         quota_pct=status.five_hour_pct)
        except Exception:
            pass
        fresh_stats = dict(stats)
        fresh_stats["quota_pct"] = status.five_hour_pct
        fresh_stats["quota_reset_at"] = reset_at
        threading.Thread(
            target=_execute_quota_trigger,
            args=(fresh_stats, project_path, session_id),
            daemon=True,
        ).start()
        fired_any = True

    if fired_any:
        quota_triggered_windows.add(reset_at)
        _save_quota_triggered_windows(quota_triggered_windows)
    return now


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
    quota_warned_windows: set = _load_quota_warned_windows()  # quota_reset_at → already spoke the 75% heads-up, disk-backed
    quota_triggered_windows: set = _load_quota_triggered_windows()  # quota_reset_at → already fired the 90% hard trigger, disk-backed
    quota_resume_verified: set = _load_quota_resume_verified()  # "session_id::reset_at" → already ran Phase 4 for this session+window, disk-backed
    idle_triggered: dict = _load_idle_triggered()  # "project_path::session_id" → {"turn_stop_ts", "recorded_at"}, disk-backed
    session_first_seen: dict = _load_session_first_seen()  # session_id → epoch first observed, disk-backed (survives restarts)
    session_parent: dict = _load_session_parent()  # session_id → parent_session_id, disk-backed, best-effort (see docstring)
    last_independent_quota_poll: float = 0.0  # throttle for _poll_independent_quota_and_fire, in-memory only —
                                               # a restart just means the next poll happens sooner, never a problem

    def _on_term(sig, frame):
        _log("received SIGTERM — stopping")
        _stop_caffeinate()
        _clear_pid()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    try:
        while True:
            active = _session_is_active()

            if active and not was_active:
                _log(f"session active")
                _start_caffeinate()
            elif not active and was_active:
                _log("session ended or went idle")
                _stop_caffeinate()

            was_active = active

            # Independent of the active/idle branch below on purpose — quota is
            # account-wide and this must not depend on _session_is_active() or
            # any per-project stats file staying fresh (see the function's own
            # docstring for the confirmed-live bug this closes).
            last_independent_quota_poll = _poll_independent_quota_and_fire(
                last_independent_quota_poll, quota_triggered_windows, session_parent,
            )

            if active:
                # Scan ALL active projects every poll — not just the most recently updated one.
                # When two sessions run simultaneously (e.g. askr + leaps) each gets checked
                # independently. Triggers are handled sequentially; pre-compact is the backstop
                # for a second project that spikes while the first is being handled.
                all_stats = _read_all_stats()

                companioned_sessions = _prune_companioned_sessions(companioned_sessions)
                session_first_seen = _prune_session_first_seen(session_first_seen)
                session_parent = _prune_session_parent(session_parent, session_first_seen)
                idle_triggered = _prune_idle_triggered(idle_triggered)

                # Sort highest context first so the most urgent project is handled first
                for stats in sorted(all_stats, key=lambda s: s.get("context_pct", 0), reverse=True):
                    _evaluate_session_triggers(
                        stats, session_first_seen, quota_warned_windows,
                        companioned_sessions, last_trigger_at,
                        quota_triggered_windows, idle_triggered,
                        session_parent, quota_resume_verified,
                    )

                time.sleep(POLL_ACTIVE)
            else:
                time.sleep(POLL_IDLE)

            # Source self-watch: if any .py file in the askr package changed since
            # startup, exit cleanly. launchd KeepAlive:true restarts us with the
            # new code — no manual daemon restart needed after a git pull.
            #
            # Found 2026-09-05: this used to exit unconditionally, same as any
            # other restart — but _execute_quota_trigger's Escape/wait/cont
            # sequence runs on a daemon=True background thread with no
            # persisted state; sys.exit(0) kills it instantly mid-wait with no
            # chance to finish, no fallback, nothing. _stop_caffeinate() right
            # below already refuses to release the sleep lock while a
            # quota-wait is in flight — this is the same guard applied to the
            # restart decision itself, not just the lock: defer the restart
            # (checked again next poll cycle) rather than abandon the wait.
            if _max_source_mtime() > _STARTUP_SOURCE_MTIME and _quota_wait_in_flight():
                _log("source files updated but a quota-wait thread is in flight — "
                     "deferring the restart until it finishes")
            elif _max_source_mtime() > _STARTUP_SOURCE_MTIME:
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
