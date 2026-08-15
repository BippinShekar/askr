#!/usr/bin/env python3
"""
Claude Code Hook - PreCompact

Emergency fallback — fires when Claude is about to auto-compact the context.
The 70% daemon trigger (Trigger A) should prevent this from firing in normal
operation. When it does fire — a single-turn context spike, quota exhaustion,
or the user choosing to keep typing into an already-full session instead of
switching to a companion — the ONLY thing that has to win a race against
Claude Code's own compaction is the SIGTERM. Everything else (checkpoint
content, notification, opening a companion) happens AFTER the kill, off this
hook's critical path.

This used to run the full heavy checkpoint (LLM handover call, architecture
regen, git commit+push, Discord webhook) synchronously BEFORE sending SIGTERM.
That pipeline involves multiple network calls and routinely took longer than
Claude Code's own compaction — so compaction finished first, defeating the
entire mechanism (confirmed 2026-08-08: a live session sat at 73% "Compacting
conversation..." while askr's kill was still stuck in git push/Discord).
Kill first, checkpoint after — same principle as the module's original claim
("killing the process is the only way to guarantee a fresh session instead of
a compressed one"), just actually honored now.

PreCompact cannot block compaction via its return value — killing the process
is the only way to guarantee a fresh session instead of a compressed one.
"""

import sys
import os
import json
import signal
import subprocess
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer
from askr.session.lifecycle import _find_session_pid

_CHECKPOINT_PENDING     = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
_NOTIFIED_SESSIONS_PATH = os.path.expanduser("~/.config/askr/emergency_notified_sessions.json")
QUOTA_HIGH              = 70.0  # treat as quota-exhausted if above this


def _get_tty_for_pid(pid: int) -> str | None:
    """tty device (e.g. 'ttys003') the given pid's stdio is attached to, or
    None if it has no controlling terminal (headless/backgrounded)."""
    try:
        out = subprocess.run(
            ["ps", "-o", "tty=", "-p", str(pid)],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        if not out or out in ("?", "??"):
            return None
        return out
    except Exception:
        return None


def _reset_terminal_mouse_tracking(tty: str):
    """Disable xterm mouse-tracking modes directly on the tty device, so a
    killed session's terminal doesn't spend the rest of its life echoing raw
    SGR mouse reports as garbage text. Also re-shows the cursor, which the
    same modes commonly hide."""
    device = tty if os.path.isabs(tty) else f"/dev/{tty}"
    try:
        with open(device, "w") as f:
            f.write("\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l\x1b[?25h")
    except Exception:
        pass


def _load_notified_sessions() -> set:
    try:
        with open(_NOTIFIED_SESSIONS_PATH) as f:
            return set(json.load(f))
    except Exception:
        return set()


def _mark_session_notified(session_id: str):
    """
    Per-session dedup for the notification+voice pair — deliberately not a
    time cooldown. A session sitting near 100% context can re-fire PreCompact
    on every subsequent message if the user keeps typing there instead of
    switching to the companion; the checkpoint+kill above must still run
    every one of those times (that part is genuinely needed each time
    compaction is imminent), but the user only needs to be told once per
    session, not once per message.
    """
    if not session_id:
        return
    try:
        sessions = _load_notified_sessions()
        sessions.add(session_id)
        os.makedirs(os.path.dirname(_NOTIFIED_SESSIONS_PATH), exist_ok=True)
        with open(_NOTIFIED_SESSIONS_PATH, "w") as f:
            json.dump(sorted(sessions), f)
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


def _session_duration_minutes(transcript_path: str) -> int:
    """
    Wall-clock span from this transcript's first to last message timestamp —
    fast, local, no LLM/network call. Used only for the notification's "N
    minutes of work preserved" framing; never gates any behavior, so a bad
    read just means an empty duration clause, not a broken checkpoint.
    """
    try:
        first_ts = last_ts = None
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ts = json.loads(line).get("timestamp")
                except Exception:
                    continue
                if not ts:
                    continue
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
        if not first_ts or not last_ts:
            return 0
        start = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
        end = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        return max(0, int((end - start).total_seconds() // 60))
    except Exception:
        return 0


def _finish_emergency_checkpoint(project_path: str, developer: str, transcript_path: str,
                                  session_id: str, should_open_companion: bool, already_notified: bool):
    """
    Runs entirely AFTER the kill, in a detached process (see _spawn_background_finish —
    a plain thread would die with this hook's own process exit). Does the heavy
    checkpoint (LLM handover, architecture regen, git push, Discord), then — only
    if this session hasn't already been told once — writes the visible
    notification, speaks a short line, and opens a companion if none is
    already running for this project.
    """
    if not session_id and transcript_path:
        # Every "companion_spawned" event logged in production so far has
        # shown up with parent_session_id "" (confirmed 2026-08-15 across
        # every emergency-trigger row in events.jsonl) — the session_id this
        # function received was empty even though the transcript_path that
        # produced it wasn't, breaking askr graph's parent/child lineage for
        # every emergency-spawned companion. Re-derive from transcript_path
        # (same computation main() does) as a cheap, always-available backstop
        # rather than propagating an empty id into launch_mode.json and the
        # event log.
        session_id = os.path.basename(transcript_path).replace(".jsonl", "")

    from askr.session.checkpoint import create_checkpoint
    checkpoint_result = create_checkpoint(
        trigger_type="emergency", developer=developer, transcript_path=transcript_path,
    )

    stats = _latest_stats()
    quota = stats.get("quota_pct")
    if quota is not None and quota >= QUOTA_HIGH:
        try:
            os.makedirs(os.path.dirname(_CHECKPOINT_PENDING), exist_ok=True)
            with open(_CHECKPOINT_PENDING, "w") as f:
                json.dump({
                    "trigger": "quota",
                    "quota_pct": quota,
                    "context_pct": stats.get("context_pct", 0),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, f)
        except Exception:
            pass

    if already_notified:
        return

    duration = _session_duration_minutes(transcript_path)
    duration_clause = f" ({duration}m of work preserved)" if duration > 0 else ""

    if should_open_companion:
        visible_message = (
            f"Askr stopped this session before Claude's built-in compaction could "
            f"compress its context{duration_clause} — a companion session is opening "
            f"now with that same full memory. You can keep using this chat if you'd "
            f"like; we won't interrupt it again."
        )
        voice_message = ("Stopped this session before compaction could compress it. "
                          "Opening a companion now with full memory. Won't interrupt again.")
    else:
        visible_message = (
            f"Askr stopped this session before Claude's built-in compaction could "
            f"compress its context{duration_clause} — switch to the companion session "
            f"already open in another window for full, uncompressed memory. You can "
            f"keep using this chat if you'd like; we won't interrupt it again."
        )
        voice_message = ("Stopped this session before compaction could compress it. "
                          "Switch to your companion session for full memory. Won't interrupt again.")

    try:
        from askr.session.lifecycle import _NOTIFICATION_PATH, _load_allowed_tools
        allowed_tools = _load_allowed_tools(project_path) if project_path else []
        prompt = ("Your previous session's context was preserved before Claude's native "
                  "compaction could compress it — read the handover file, it has the full, "
                  "uncompressed state. Continue immediately. Work autonomously.")
        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump({
                "type": "compaction_prevented",
                "message": visible_message,
                "opened_companion": should_open_companion,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": prompt,
                "shown": False,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, f)
    except Exception:
        pass

    _speak(voice_message)

    if should_open_companion:
        try:
            import shutil
            from askr.session.lifecycle import _spawn_terminal_app_fallback, _write_launch_mode, _get_next_goal, _NOTIFICATION_PATH
            from askr.state.writer import append_event

            state_dir = os.path.join(project_path, "askr_state")
            next_goal = _get_next_goal(state_dir)
            _write_launch_mode(next_goal, parent_session_id=session_id)

            allowed_tools = _load_allowed_tools(project_path)
            claude_bin = shutil.which("claude") or "claude"
            tools_flag = f" --allowedTools {','.join(allowed_tools)}" if allowed_tools else ""
            spawn_prompt = prompt.replace("'", "").replace('"', "").replace("\\", "")

            _spawn_terminal_app_fallback(project_path, claude_bin, tools_flag, spawn_prompt, _NOTIFICATION_PATH)
            append_event("companion_spawned", project_path, parent_session_id=session_id, trigger_type="emergency")
        except Exception:
            pass


def _spawn_background_finish(project_path: str, developer: str, transcript_path: str,
                              session_id: str, should_open_companion: bool, already_notified: bool):
    """
    Detached process, not a thread — this hook's own Python process exits
    right after main() returns, which would kill a daemon thread before it
    finishes. Same start_new_session=True Popen pattern lifecycle.py already
    uses for its Terminal.app fallback worker.
    """
    try:
        from askr.session.lifecycle import _ASKR_ROOT
        code = (
            f"import sys; sys.path.insert(0, {_ASKR_ROOT!r})\n"
            f"from askr.hooks.pre_compact import _finish_emergency_checkpoint as f\n"
            f"f({project_path!r}, {developer!r}, {transcript_path!r}, {session_id!r}, "
            f"{should_open_companion!r}, {already_notified!r})\n"
        )
        subprocess.Popen(
            [sys.executable, "-c", code],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    from askr.utils.hook_capture import capture_hook_payload
    capture_hook_payload("PreCompact", payload)

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")
    session_id = os.path.basename(transcript_path).replace(".jsonl", "") if transcript_path else ""

    from askr.session.monitor import find_project_root
    project_path = find_project_root()

    pid = _find_session_pid(transcript_path)

    if not pid:
        # No live process to race against compaction for — nothing to kill, so
        # the heavy checkpoint can run synchronously; there's no SIGTERM-vs-
        # compaction race in this branch, only the kill needs to be fast.
        from askr.session.checkpoint import create_checkpoint
        checkpoint_result = create_checkpoint(
            trigger_type="emergency", developer=developer, transcript_path=transcript_path,
        )
        if checkpoint_result.get("git_pushed", False):
            instructions = "Askr has checkpointed state to git. A new session will resume from the handover."
        else:
            instructions = ("Askr checkpointed state LOCALLY, but the git push failed "
                             "(see ~/.config/askr/checkpoint_error.log). The handover exists "
                             "on disk but has not reached the remote — check git status before "
                             "assuming another machine can resume from it.")
        print(json.dumps({"custom_instructions": instructions}))
        return

    from askr.session.lifecycle import _find_all_claude_pids_by_project
    other_pids = [p for p in _find_all_claude_pids_by_project(project_path) if p != pid] if project_path else []

    # Resolve the controlling tty BEFORE the kill below — `ps -p pid` returns
    # nothing once the process is dead, so this has to happen while it's
    # still alive.
    tty = _get_tty_for_pid(pid)

    # Delete own stats file before dying — prevents the daemon from re-triggering
    # on a dead session's stale high ctx% after the cooldown expires.
    if transcript_path and project_path:
        try:
            from askr.session.monitor import stats_path_for_session
            sp = stats_path_for_session(project_path, session_id)
            if os.path.exists(sp):
                os.remove(sp)
        except Exception:
            pass

    # THE race: kill before Claude Code's own compaction can finish. Nothing
    # above this line does network I/O or an LLM call — everything that does
    # happens below, after the kill, off this hook's critical path.
    #
    # SIGKILL, not SIGTERM: confirmed 2026-08-15 that SIGTERM lost the race
    # even with kill-first ordering — Claude Code's process finished the
    # in-flight compaction AND generated its next response before actually
    # exiting, meaning it was treating SIGTERM as "finish current work, then
    # exit" rather than dying on receipt. SIGKILL can't be caught, blocked,
    # or deferred by the target process, so there's no handler left to honor.
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    # SIGKILL leaves no room for Claude Code's TUI to run its own exit
    # handler, which is what would normally disable the xterm mouse-tracking
    # mode (\x1b[?1000h/?1003h/?1006h) it enables on start. Left alone, every
    # mouse move over that terminal pane afterward gets SGR-encoded and
    # dumped onto the screen as unreadable noise ("35;92;25M35;76;28M...") —
    # confirmed live 2026-08-16, looks exactly like a corrupted terminal or a
    # virus to anyone who doesn't recognize SGR mouse reporting. Writing the
    # disable sequence straight to the tty device (same mechanism the
    # `write`/`wall` commands use) bypasses the now-dead shell entirely, so
    # it doesn't depend on the extension's notification round-trip or on
    # zsh's line editor faithfully relaying raw escape bytes it was never
    # meant to interpret.
    if tty:
        _reset_terminal_mouse_tracking(tty)

    already_notified = session_id in _load_notified_sessions()
    if session_id:
        _mark_session_notified(session_id)

    _spawn_background_finish(project_path, developer, transcript_path, session_id,
                              not other_pids, already_notified)


if __name__ == "__main__":
    main()
