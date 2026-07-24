#!/usr/bin/env python3
"""
Claude Code Hook - SessionStart

Fires at the start of every Claude Code session.
Pulls latest state from git, then injects project context.

Goal suggestion: if today has no goals set, calls Haiku with the last
handover to suggest 1-2 actionable goals and adds them automatically.

If started by the lifecycle daemon (launch_mode.json present), injects
the next goal as an explicit task directive.
"""

import sys
import os
import json
import subprocess
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.reader import build_context_injection
from askr.state.goals import format_for_context as goals_context
from askr.state.config import get_state_dir, load_developer

_LAUNCH_MODE_PATH  = os.path.expanduser("~/.config/askr/launch_mode.json")
_SESSIONS_DIR      = os.path.expanduser("~/.config/askr")
_NOTIFICATION_PATH = os.path.expanduser("~/.config/askr/notification.json")


def _sessions_path(developer: str) -> str:
    return os.path.join(_SESSIONS_DIR, f"claude_sessions_{developer}.json")


def _write_claude_pid(developer: str):
    """
    Find the running Claude process for this project and append its PID to the
    per-developer sessions registry. Supports parallel sessions — each registers
    its own PID so the daemon can kill all of them.
    """
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
                        path = _sessions_path(developer)
                        os.makedirs(_SESSIONS_DIR, exist_ok=True)
                        registry = []
                        try:
                            with open(path) as f:
                                registry = json.load(f)
                        except Exception:
                            registry = []
                        # Prune dead PIDs, then add this one
                        import signal as _sig
                        live = []
                        for p in registry:
                            try:
                                os.kill(p, 0)
                                live.append(p)
                            except OSError:
                                pass
                        if pid not in live:
                            live.append(pid)
                        with open(path, "w") as f:
                            json.dump(live, f)
                        return
            except Exception:
                continue
    except Exception:
        pass


def git_pull() -> bool:
    try:
        result = subprocess.run(["git", "pull", "--quiet"], capture_output=True, timeout=15)
        return result.returncode == 0
    except Exception:
        return False


def _read_launch_mode() -> dict:
    try:
        if not os.path.exists(_LAUNCH_MODE_PATH):
            return {}
        with open(_LAUNCH_MODE_PATH) as f:
            data = json.load(f)
        if not data.get("active"):
            return {}
        ts = data.get("timestamp", "")
        if ts:
            written = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - written > timedelta(minutes=5):
                return {}
        with open(_LAUNCH_MODE_PATH, "w") as f:
            json.dump({"active": False}, f)
        return data
    except Exception:
        return {}


def _archive_stale_goals():
    """
    Move uncompleted goals from past-dated sections to backlog.
    Runs before goal suggestion so stale goals don't block inference.
    """
    try:
        from askr.state.goals import archive_stale_goals
        archive_stale_goals()
    except Exception:
        pass


def _notify_stale_goals():
    """
    If any timestamped goals are 6+ hours old, write a goal_check notification
    so the IDE extension surfaces them for the user to resolve.
    """
    try:
        import json as _json
        from askr.state.goals import get_stale_goals
        stale = get_stale_goals(hours=6)
        if not stale:
            return
        notification_path = os.path.expanduser("~/.config/askr/notification.json")
        goal_lines = "\n".join(f"  - {text} ({h}h ago)" for text, _, h in stale)
        payload = {
            "type": "goal_check",
            "message": f"{len(stale)} goal(s) haven't moved in 6+ hours:\n{goal_lines}",
            "goals": [{"text": t, "added": a, "hours": h} for t, a, h in stale],
            "shown": False,
            "timestamp": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        }
        os.makedirs(os.path.dirname(notification_path), exist_ok=True)
        with open(notification_path, "w") as f:
            _json.dump(payload, f)
    except Exception:
        pass


def _maybe_suggest_goals(developer: str) -> list[str]:
    """
    If today has no goals, suggest 1-2 from the last handover via Haiku.
    Adds them to goals.jsonl and returns the list (empty if skipped/failed).
    Never blocks session start — all errors are swallowed.
    """
    try:
        from askr.state.goals import load_today_goals, suggest_goals_from_handover, add_goal
        if load_today_goals():
            return []  # user already has goals — don't touch them
        suggestions = suggest_goals_from_handover(developer)
        for g in suggestions:
            add_goal(g, "today", auto_suggested=True)
        return suggestions
    except Exception:
        return []


def _drain_task_queue(developer: str) -> list[dict]:
    """
    Read pending tasks from askr_state/tasks/queue_<developer>.jsonl.
    Archive to done_<developer>.jsonl, clear the queue.
    Returns list of task dicts. Never blocks session start.

    Locked against the same .lock sidecar `askr task queue` appends under
    (askr/state/writer.py:file_lock) — without it, a task appended between
    this read and the truncate below gets silently wiped, no error, no trace.
    """
    try:
        import json as _json
        from askr.state.config import get_state_dir
        from askr.state.writer import file_lock
        tasks_dir  = os.path.join(get_state_dir(), "tasks")
        queue_path = os.path.join(tasks_dir, f"queue_{developer}.jsonl")
        done_path  = os.path.join(tasks_dir, f"done_{developer}.jsonl")

        if not os.path.exists(queue_path):
            return []

        with file_lock(queue_path):
            tasks = []
            with open(queue_path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            tasks.append(_json.loads(line))
                        except Exception:
                            pass

            if not tasks:
                return []

            drain_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(done_path, "a") as f:
                for t in tasks:
                    t["drained_at"] = drain_ts
                    f.write(_json.dumps(t) + "\n")

            # Clear queue
            open(queue_path, "w").close()
        return tasks
    except Exception:
        return []


def _peek_task_queue(developer: str) -> list[dict]:
    """Read pending tasks without draining/truncating — used when the session
    is in a dangerous-permission state and tasks must stay queued (held, not
    dropped) until approved via `askr task approve`."""
    try:
        import json as _json
        tasks_dir  = os.path.join(get_state_dir(), "tasks")
        queue_path = os.path.join(tasks_dir, f"queue_{developer}.jsonl")
        if not os.path.exists(queue_path):
            return []
        tasks = []
        with open(queue_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        tasks.append(_json.loads(line))
                    except Exception:
                        pass
        return tasks
    except Exception:
        return []


def _consume_approval_flag(developer: str) -> bool:
    """One-shot bypass written by `askr task approve <dev>`. Consuming it here
    (not a permanent setting) means each held batch needs its own explicit
    approval — approving once doesn't silently authorize every future batch."""
    flag_path = os.path.join(get_state_dir(), "tasks", f"approved_{developer}.flag")
    if os.path.exists(flag_path):
        try:
            os.remove(flag_path)
        except Exception:
            pass
        return True
    return False


def _notify_tasks_held(developer: str, tasks: list[dict], reasons: list[str]):
    task_list   = "\n".join(f"- [{t.get('from','?')}] {t.get('desc','')}" for t in tasks)
    reason_text = "; ".join(reasons)
    message = (
        f"{len(tasks)} queued task(s) held for {developer} — this session has {reason_text}, "
        f"so askr did not run them automatically. "
        f"Run `askr task approve {developer}` to release them, or `askr task discard {developer}` to drop them.\n\n{task_list}"
    )
    try:
        payload = {
            "type": "task_approval_pending",
            "message": message,
            "developer": developer,
            "tasks": tasks,
            "reasons": reasons,
            "shown": False,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        pass
    try:
        from askr.clients.discord import send_message
        send_message(f"🛑 **[askr] Tasks held — approval needed**\n{message}")
    except Exception:
        pass


def _reset_stats_for_project(source: str = "", session_id: str = ""):
    """
    Write a stats entry for the new session immediately on session start.
    Only a "startup" or "clear" source is a genuinely empty context — zero it
    so the status bar snaps to ctx:0% for the right project rather than
    showing stale stats from a different one.

    "resume" and "compact" sessions already carry real context from the
    existing transcript, so we compute the actual usage instead of zeroing it;
    writing 0% there was misleading the status bar into showing an empty
    context right after a resume/compact that still had real tokens loaded.
    Quota fields are preserved either way — they're per-account and still valid.

    Written to this session's own per-session stats file, not a shared
    per-project one — a shared file gets touched by every session start
    (including askr's own companion sessions) and stays at 0% forever since
    nothing updates it again after this, permanently haunting any code that
    scans all stats files for a project as a second, phantom 0% session.
    """
    if not session_id:
        return
    try:
        from askr.session.monitor import stats_path_for_session, find_project_root, get_session_stats
        project_path = find_project_root()
        stats_path   = stats_path_for_session(project_path, session_id)
        existing = {}
        try:
            with open(stats_path) as f:
                existing = json.load(f)
        except Exception:
            pass

        context_pct    = 0.0
        context_tokens = 0
        output_tokens  = 0
        context_window = 200000
        turns          = 0
        model          = existing.get("model", "")

        if source in ("resume", "compact"):
            stats = get_session_stats(project_path, session_id)
            if stats:
                context_pct    = stats.context_pct
                context_tokens = stats.context_tokens
                output_tokens  = stats.output_tokens
                context_window = stats.context_window
                turns          = stats.turns
                model          = stats.model
                session_id     = stats.session_id

        os.makedirs(os.path.dirname(stats_path), exist_ok=True)
        with open(stats_path, "w") as f:
            json.dump({
                "project_path":    project_path,
                "context_pct":     round(context_pct, 4),
                "context_tokens":  context_tokens,
                "output_tokens":   output_tokens,
                "context_window":  context_window,
                "context_label":   "ok",
                "turns":           turns,
                "next_trigger":    None,
                # Preserve quota fields — they're API-sourced and still valid
                "quota_pct":       existing.get("quota_pct"),
                "quota_reset_at":  existing.get("quota_reset_at"),
                "quota_7d_pct":    existing.get("quota_7d_pct"),
                "quota_updated_at": existing.get("quota_updated_at"),
                "model":           model,
                "session_id":      session_id,
                "updated_at":      datetime.now(timezone.utc).isoformat(),
            }, f)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    _reset_stats_for_project(payload.get("source", ""), payload.get("session_id", ""))

    pull_ok = True
    if os.path.isdir(get_state_dir()):
        pull_ok = git_pull()

    try:
        from askr.state.analytics import record_session_start
        record_session_start()
    except Exception:
        pass

    developer = load_developer()
    session_id = payload.get("session_id", "")
    _write_claude_pid(developer)

    if session_id:
        try:
            from askr.utils.retry import import_retry

            def _register():
                from askr.session.registry import register_session
                register_session(session_id, developer)

            import_retry(_register)
        except Exception:
            pass

    queued_tasks = []
    held_tasks = []
    held_reasons = []
    try:
        from askr.session.permission_gate import is_dangerous_session
        dangerous, held_reasons = is_dangerous_session(os.path.dirname(get_state_dir()))
    except Exception:
        dangerous = False

    if dangerous and not _consume_approval_flag(developer):
        # Exclude tasks a queuer (e.g. leaps-bug-reporter) already marked
        # "fixed" — they were never drained from the queue file (no per-task
        # discard existed until now), so without this filter every already-
        # resolved bug kept inflating the held count and cluttering the
        # notice indefinitely.
        held_tasks = [t for t in _peek_task_queue(developer) if t.get("status") != "fixed"]
        if held_tasks:
            _notify_tasks_held(developer, held_tasks, held_reasons)
    else:
        queued_tasks = _drain_task_queue(developer)

    _archive_stale_goals()
    _notify_stale_goals()
    suggested_goals = _maybe_suggest_goals(developer)

    state_context = build_context_injection()
    goals = goals_context()
    launch_mode = _read_launch_mode()

    parts = []
    if state_context:
        parts.append(state_context)
    if goals:
        parts.append(goals)

    if suggested_goals:
        goal_list = "\n".join(f"- {g}" for g in suggested_goals)
        parts.append(
            f"## Goals Auto-Suggested\n\n"
            f"No goals were set for today. Askr inferred these from your last session's handover "
            f"and added them automatically:\n\n{goal_list}\n\n"
            f"Run `askr goals` to review or `askr goal add \"...\"` to add more."
        )

    if queued_tasks:
        task_list = "\n".join(f"- [{t.get('from','?')}] {t['desc']}" for t in queued_tasks)
        parts.append(
            f"## Tasks Queued by Your Team\n\n"
            f"Your teammates queued {len(queued_tasks)} task(s) for this session. "
            f"Work through them after completing any in-progress work from the handover above:\n\n"
            f"{task_list}"
        )

    if held_tasks:
        parts.append(
            f"## Tasks Held — Pending Confirmation\n\n"
            f"{len(held_tasks)} teammate-queued task(s) exist but were NOT loaded into this session: "
            f"{'; '.join(held_reasons)}. "
            f"Do not attempt them. The developer can run `askr task approve {developer}` to release them "
            f"or `askr task discard {developer}` to drop them."
        )

    if launch_mode.get("goal"):
        goal_text = launch_mode["goal"]
        parts.append(
            f"## Active Goal (Autonomous Session)\n\n"
            f"This session was started automatically by askr after a context or quota checkpoint. "
            f"Pick up from the handover above and work on:\n\n**{goal_text}**\n\n"
            f"Continue autonomously. When done, the session will be checkpointed again."
        )

    if not pull_ok:
        parts.insert(0,
            "⚠️ WARNING: git pull failed at session start. "
            "Team task queue and shared state may be stale. "
            "Run `git pull` manually before making changes, or your work may conflict with teammates'."
        )

    if session_id:
        try:
            from askr.utils.retry import import_retry

            def _get_siblings():
                from askr.session.registry import get_active_sessions
                return get_active_sessions(exclude_session_id=session_id)

            siblings = import_retry(_get_siblings)
            if siblings:
                lines = []
                for s in siblings:
                    dev = s.get("dev", "?")
                    hb = s.get("last_heartbeat", "")
                    try:
                        age_min = int(
                            (datetime.now(timezone.utc) - datetime.fromisoformat(hb)).total_seconds() / 60
                        )
                        age_str = f"{age_min}m ago"
                    except Exception:
                        age_str = "recently"
                    lines.append(f"- **{dev}** (last active: {age_str})")
                parts.append(
                    "## Active Parallel Sessions\n\n"
                    "Other Claude sessions are running on this project right now. "
                    "Check their handover files before touching shared files:\n\n"
                    + "\n".join(lines)
                )
        except Exception:
            pass

    if parts:
        print(json.dumps({"context": "\n\n".join(parts)}))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
