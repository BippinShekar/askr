#!/usr/bin/env python3
"""
Claude Code Hook - Stop

Fires when a Claude Code session ends.
Delegates to checkpoint.create_checkpoint for handover, state update, commit+push.
"""

import sys
import os
import json
import subprocess
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer

_CHECKPOINT_PENDING = os.path.expanduser("~/.config/askr/checkpoint_pending.json")
_NOTIFICATION_PATH  = os.path.expanduser("~/.config/askr/notification.json")
_TURN_STOP_DIR      = os.path.expanduser("~/.config/askr/turn_stops")


def _signal_turn_stopped(session_id: str):
    """
    Mark that this session's current turn has genuinely finished — the Stop hook
    firing is the only authoritative "reply is done" signal Claude Code gives us.
    lifecycle.py's companion-session trigger polls this marker's mtime instead of
    guessing from JSONL write-silence, which false-positives during any long-running
    tool call (e.g. a multi-minute git-filter-repo run) that just happens to pause
    writes for >30s mid-turn.
    """
    if not session_id:
        return
    try:
        os.makedirs(_TURN_STOP_DIR, exist_ok=True)
        with open(os.path.join(_TURN_STOP_DIR, f"{session_id}.json"), "w") as f:
            json.dump({"stopped_at": datetime.utcnow().isoformat() + "Z"}, f)
    except Exception:
        pass


def _update_allowed_tools(transcript_path: str):
    """Extract tool names from session JSONL and persist to allowedTools + permissions.allow."""
    if not transcript_path or not os.path.exists(transcript_path):
        return

    tools_used = set()
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                if obj.get("type") == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "")
                            if name:
                                tools_used.add(name)
    except Exception:
        return

    if not tools_used:
        return

    project_dir = os.path.join(os.getcwd(), ".claude")

    try:
        settings_path = os.path.join(project_dir, "settings.json")
        if os.path.exists(settings_path):
            with open(settings_path) as f:
                settings = json.load(f)
        else:
            settings = {}

        existing = set(settings.get("allowedTools", []))
        if tools_used - existing:
            settings["allowedTools"] = sorted(existing | tools_used)
            os.makedirs(project_dir, exist_ok=True)
            with open(settings_path, "w") as f:
                json.dump(settings, f, indent=2)
    except Exception:
        pass

    # permissions.allow in settings.local.json is what actually silences prompts
    try:
        local_path = os.path.join(project_dir, "settings.local.json")
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
    except Exception:
        pass


def _advance_launch_goal():
    """If daemon is running, update launch_mode.json with the next open goal."""
    try:
        from askr.session.lifecycle import daemon_is_running
        if not daemon_is_running():
            return
        from askr.session.lifecycle import _get_next_goal, _write_launch_mode, _LAUNCH_MODE_PATH
        import os as _os, json as _json
        active = False
        try:
            if _os.path.exists(_LAUNCH_MODE_PATH):
                with open(_LAUNCH_MODE_PATH) as f:
                    active = _json.load(f).get("active", False)
        except Exception:
            pass
        if active:
            next_goal = _get_next_goal()
            _write_launch_mode(next_goal)
    except Exception:
        pass


def _live_stats(project_path: str) -> dict:
    """Freshest real session_stats.json for this project — used so any percentage
    spoken from a pending checkpoint always reflects current reality rather than
    whatever quota_pct/context_pct happened to be cached in checkpoint_pending.json
    at write time."""
    try:
        from askr.session.monitor import find_project_stats_files
        candidates = sorted(find_project_stats_files(project_path), key=os.path.getmtime, reverse=True)
        for path in candidates:
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                continue
    except Exception:
        pass
    return {}


def _write_relaunch_notification_if_pending(checkpoint_result: dict) -> bool:
    """
    If the daemon flagged a pending checkpoint, write the re-launch notification
    using the already-completed stop checkpoint result.

    The stop checkpoint (create_checkpoint) ALWAYS runs first — this function
    only decides whether to open a new autonomous session afterward.

    - trigger==context: write IDE notification to open a new session immediately
    - trigger==quota:   write notification informing quota is high; daemon waits
    """
    try:
        if not os.path.exists(_CHECKPOINT_PENDING):
            return False
        with open(_CHECKPOINT_PENDING) as f:
            pending = json.load(f)
        # Do NOT delete checkpoint_pending yet — only delete after notification is
        # successfully written. If writing fails, the flag stays and the daemon's
        # 20s fallback kicks in instead of silently dropping the continuation.
    except Exception:
        return False

    # If the flag was written more than 5 min ago and the session continued past
    # it, treat it as stale — the user finished their work voluntarily. A missing
    # or unparseable timestamp must ALSO count as stale, not skip this check: this
    # file is only ever fully populated by pre_compact.py's emergency path now
    # (the daemon's own writer for context-triggered checkpoints was removed in
    # 65e543b), so a malformed/legacy file with no valid timestamp is garbage,
    # never something to trust and act on as if it just happened.
    is_stale = True
    try:
        written_at = pending.get("timestamp", "")
        if written_at:
            import datetime as _dt_check
            written = _dt_check.datetime.fromisoformat(written_at)
            age_s = (_dt_check.datetime.now(_dt_check.timezone.utc) - written).total_seconds()
            is_stale = age_s > 300
    except Exception:
        is_stale = True
    if is_stale:
        try:
            os.remove(_CHECKPOINT_PENDING)
        except Exception:
            pass
        return False

    try:
        from askr.session.lifecycle import (
            _get_next_goal, _write_launch_mode, _load_allowed_tools,
            _infer_direction, _read_session_arc,
        )
        from askr.state.config import load_developer
        import datetime as _dt

        trigger = pending.get("trigger", "context")

        next_goal = _get_next_goal()
        _write_launch_mode(next_goal)

        project_path  = os.getcwd()
        allowed_tools = _load_allowed_tools(project_path)
        now           = _dt.datetime.now(_dt.timezone.utc).isoformat()

        # Never speak a percentage sourced only from checkpoint_pending.json —
        # it's a hand-off flag, not a live reading, and can carry an arbitrarily
        # stale number even when its own timestamp looks fresh (e.g. pre_compact.py
        # writes it once at kill-time; by the time this Stop hook runs seconds or
        # minutes later in a NEW session, the account's real quota/context may have
        # already moved). Always prefer whatever the current stats file says now.
        live_stats = _live_stats(project_path)

        if trigger == "quota":
            quota_pct = live_stats.get("quota_pct", pending.get("quota_pct", 0))
            pct_str   = f"{round(quota_pct)}%" if quota_pct else "high"
            payload = {
                "type": "quota",
                "message": f"Quota at {pct_str} — state saved. Askr will resume after reset.",
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "shown": False,
                "timestamp": now,
            }
        else:
            pct       = live_stats.get("context_pct", pending.get("context_pct", 0))
            pct_str   = f"{round(pct * 100)}%"
            developer = load_developer()

            # Build direction from ground-truth signals, not from handover speculation
            direction = _infer_direction(project_path)
            confidence = direction["confidence"]

            if confidence >= 0.70:
                # High-confidence: session prompt leads with the inferred direction.
                # The handover provides context; direction provides the directive.
                arc = _read_session_arc(developer) if direction["signal_source"] == "git_momentum" else ""
                arc_part = f" Context from recent sessions: {arc}" if arc else ""
                stop_prompt = (
                    f"Continue work on: {direction['direction']}. "
                    f"Read the handover file for context on where the last session left off.{arc_part} "
                    f"Work autonomously."
                )
            else:
                # Low-confidence: session arc as supplementary context, but gate fires in S6
                arc = _read_session_arc(developer)
                arc_part = f" Recent session arc: {arc}." if arc else ""
                stop_prompt = (
                    f"Read the handover file.{arc_part} "
                    f"Before starting any work, summarise what you plan to do and wait "
                    f"for confirmation from the user."
                )

            proposed = direction.get("proposed", False)
            # Context-cut mid-session: user was actively engaged, session was
            # interrupted. Auto-continue regardless of session type — requiring
            # manual approval for an involuntary cut defeats the point of askr.
            if trigger == "context" and proposed:
                proposed = False
                stop_prompt = (
                    f"Context was cut mid-session. Continue from where we left off: "
                    f"{direction['direction']}. Read the handover file for the full state. "
                    f"Resume the conversation or work — do not restart from scratch."
                )

            if confidence < 0.70:
                # Low-confidence: no clear direction — block, ask user what to do
                notification_type = "direction_confirm"
                signal_label = direction["signal_source"].replace("_", " ")
                message = (
                    f"Context at {pct_str} — state saved. "
                    f"Direction unclear (signal: {signal_label}, confidence: {round(confidence * 100)}%). "
                    f"What should the next session work on?"
                )
            elif proposed:
                # High-confidence from a naturally-ended talk-only session.
                # Don't auto-launch — surface for user approval.
                notification_type = "direction_proposal"
                preview = direction["direction"][:100]
                message = f"Research session concluded: {preview}"
            else:
                # Coding session or context-cut: auto-launch
                notification_type = "context"
                message = f"Context at {pct_str} — state saved to git. Opening new chat."

            payload = {
                "type": notification_type,
                "message": message,
                "goal": next_goal,
                "project_path": project_path,
                "allowed_tools": allowed_tools,
                "prompt": stop_prompt,
                "direction": direction.get("direction", ""),
                "direction_confidence": confidence,
                "direction_signal": direction["signal_source"],
                "shown": False,
                "timestamp": now,
            }

        os.makedirs(os.path.dirname(_NOTIFICATION_PATH), exist_ok=True)
        with open(_NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
        try:
            from askr.clients.voice import announce
            announce(payload["message"])
        except Exception:
            pass

        # Notification written successfully — now safe to remove the flag.
        try:
            os.remove(_CHECKPOINT_PENDING)
        except Exception:
            pass

        return True
    except Exception as _e:
        # Log the failure so it's diagnosable from daemon.log; leave
        # checkpoint_pending intact so the daemon's 20s fallback fires.
        try:
            import traceback as _tb, datetime as _dt2
            ts = _dt2.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_path = os.path.expanduser("~/.config/askr/stop_hook_error.log")
            with open(log_path, "a") as _lf:
                _lf.write(f"[{ts}] _write_relaunch_notification_if_pending failed:\n{_tb.format_exc()}\n")
        except Exception:
            pass
        return False


_DECISION_RE = __import__('re').compile(
    r"(?i)\b("
    r"we(?:'ll| will| should) use|going with|decided? to|the (?:approach|solution|fix) is|"
    r"(?:will|won't) use|should not|must not|instead (?:use|of)|the correct (?:approach|fix)|"
    r"we(?:'re| are) using|implemented? (?:as|using|with)|the right (?:approach|way)"
    r")\b"
)

# Phrases that indicate guard-rationalized operational constraints, not real decisions.
# If extracted text matches any of these, skip it — writing it creates a self-reinforcing
# block loop: guard blocks → Claude writes a "constraint" → guard reads it → blocks again.
_GUARD_SIGNAL_PHRASES = (
    "guard blocked", "write blocked", "awaiting claude correction",
    "must be documented", "requires explicit", "outside backend",
    "outside website", "file ownership rules", "merge conflicts",
    "requires approval", "must be approved", "prior to implementation",
    "before implementation", "not documented in architecture",
)


def _extract_and_save_decisions(transcript_path: str, state_dir: str):
    """Keyword-detect settled decisions in Claude's last response and append to decisions.jsonl."""
    if not transcript_path or not os.path.exists(transcript_path):
        return
    try:
        import re
        lines = []
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except Exception:
                        pass

        # Collect text from all assistant blocks in the last turn
        last_user_idx = -1
        for i, entry in enumerate(lines):
            if entry.get("type") == "user":
                last_user_idx = i

        text_parts = []
        for entry in lines[last_user_idx + 1:] if last_user_idx >= 0 else lines:
            if entry.get("type") == "assistant":
                for block in entry.get("message", {}).get("content", []):
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

        full_text = " ".join(text_parts)
        if not full_text.strip():
            return

        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        decisions = []
        for s in sentences:
            s = re.sub(r'\*+', '', s).strip()
            if 20 < len(s) < 250 and _DECISION_RE.search(s):
                s_lower = s.lower()
                if not any(sig in s_lower for sig in _GUARD_SIGNAL_PHRASES):
                    decisions.append(s)
            if len(decisions) >= 5:
                break

        if not decisions:
            return

        from askr.state.config import load_developer
        from askr.state.writer import file_lock
        developer = load_developer()
        decisions_path = os.path.join(state_dir, "decisions.jsonl")
        ts = __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")
        with file_lock(decisions_path):
            with open(decisions_path, "a") as f:
                for d in decisions:
                    f.write(json.dumps({
                        "at": ts, "dev": developer,
                        "decision": d, "reason": "",
                        "source": "transcript_extracted",
                    }) + "\n")
    except Exception:
        pass


def _broadcast_session_end(developer: str, completed_goals: list, project_path: str, duration_seconds: int = 0, autonomous: bool = False):
    try:
        from askr.session.cost import get_session_cost_summary, record_checkpoint_cost
        from askr.session.report_image import session_card
        from askr.session.checkpoint import _context_history_for_session
        from askr.clients.discord import send_file, send_message

        # collect files changed
        files_changed = []
        try:
            res = subprocess.run(
                ["git", "diff", "HEAD~1", "--name-only"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            files_changed = [
                f for f in res.stdout.strip().splitlines()
                if not f.startswith("askr_state/")
            ]
        except Exception:
            pass

        cost_summary = get_session_cost_summary(project_path)
        record_checkpoint_cost("stop", developer, cost_summary)

        duration    = duration_seconds
        context_h   = _context_history_for_session(project_path)

        img_path = session_card(
            trigger_type="stop",
            developer=developer,
            cost_summary=cost_summary,
            duration_seconds=duration,
            goals_completed=completed_goals,
            files_changed=files_changed,
            context_history=context_h,
            autonomous=autonomous,
            project_path=project_path,
        )

        caption = f"**[askr] Session ended** — {developer}"
        if completed_goals:
            caption += "\n" + "  ".join(f"✓ {g}" for g in completed_goals[:3])

        if img_path:
            sent = send_file(img_path, caption)
            try:
                os.remove(img_path)
            except Exception:
                pass
            if not sent:
                _broadcast_session_text(developer, completed_goals, project_path)
        else:
            _broadcast_session_text(developer, completed_goals, project_path)
    except Exception:
        _broadcast_session_text(developer, completed_goals, project_path)


def _broadcast_session_text(developer: str, completed_goals: list, project_path: str):
    """Text-only fallback for when image generation fails."""
    try:
        from askr.clients.discord import send_message
        lines = [f"**[askr] Session ended** — {developer}"]
        if completed_goals:
            lines.append("**Goals completed:**")
            lines.extend(f"✓ {g}" for g in completed_goals)
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "--name-only"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            files = [f for f in result.stdout.strip().splitlines() if not f.startswith("askr_state/")]
            if files:
                lines.append("**Files changed:**")
                lines.extend(f"  {f}" for f in files[:10])
                if len(files) > 10:
                    lines.append(f"  …and {len(files) - 10} more")
            msg_result = subprocess.run(
                ["git", "log", "-1", "--pretty=%s"],
                capture_output=True, text=True, cwd=project_path, timeout=5,
            )
            commit_msg = msg_result.stdout.strip()
            if commit_msg and not commit_msg.startswith("askr:"):
                lines.append(f"**Last commit:** {commit_msg}")
        except Exception:
            pass
        if len(lines) > 1:
            send_message("\n".join(lines))
    except Exception:
        pass


TURN_AWAY_THRESHOLD_SECONDS = 60  # below this, assume an active back-and-forth and stay quiet


def _turn_elapsed_seconds(transcript_path: str) -> float:
    """Seconds since the last user message in this turn — a proxy for 'did the
    user likely step away while Claude worked', since Stop fires right when a
    reply finishes and has no other signal about what the user is doing now."""
    if not transcript_path or not os.path.exists(transcript_path):
        return 0.0
    last_user_ts = None
    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user" or not obj.get("timestamp"):
                    continue
                # Tool results are logged as type "user" too (they're the next
                # turn in the API sense) — skip those, we only want messages
                # the human actually typed.
                content = obj.get("message", {}).get("content")
                if isinstance(content, list) and any(
                    isinstance(b, dict) and b.get("type") == "tool_result" for b in content
                ):
                    continue
                last_user_ts = obj["timestamp"]
    except Exception:
        return 0.0
    if not last_user_ts:
        return 0.0
    try:
        from datetime import timezone
        ts = datetime.fromisoformat(last_user_ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - ts).total_seconds()
    except Exception:
        return 0.0


# Rotated for the no-goal case so the ping doesn't say the exact same thing
# every time — the "Done." prefix is the constant, recognizable part (see
# speak_signature); this is just the detail that follows it.
_GENERIC_DONE_PHRASES = [
    "Session wrapped up.",
    "All quiet on this end.",
    "Nothing else pending.",
    "Back whenever you're ready.",
]


def _speak_session_done(completed_goals: list, transcript_path: str = ""):
    """
    Spoken 'done' ping — deliberately gated differently from the Discord card
    above (which fires on completed_goals or >=5min TOTAL session duration,
    for an async catch-up summary). Voice is a real-time signal: a completed
    goal is always worth announcing, but otherwise only speak if THIS turn ran
    long enough that the user probably tabbed away — a fast back-and-forth
    should stay silent regardless of how long the overall session has run.

    Spoken as a two-voice "sonic logo": a short "Done." prefix in one voice
    (askr's signature) followed by the detail in a second, distinct voice —
    so it doesn't sound like every other generic TTS notification.
    """
    try:
        import random
        from askr.clients.voice import announce
        if completed_goals:
            body = completed_goals[0]
        elif _turn_elapsed_seconds(transcript_path) >= TURN_AWAY_THRESHOLD_SECONDS:
            body = random.choice(_GENERIC_DONE_PHRASES)
        else:
            return
        announce(body, prefix="Done.")
    except Exception:
        pass


def _was_autonomous() -> bool:
    """True if this session was launched by askr (goal_launch or context trigger)."""
    try:
        from askr.session.lifecycle import _LAUNCH_MODE_PATH
        if os.path.exists(_LAUNCH_MODE_PATH):
            with open(_LAUNCH_MODE_PATH) as f:
                return json.load(f).get("active", False)
    except Exception:
        pass
    return False


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer       = load_developer()
    transcript_path = payload.get("transcript_path", "")
    session_id      = payload.get("session_id", "")
    autonomous      = _was_autonomous()
    _update_allowed_tools(transcript_path)
    _extract_and_save_decisions(transcript_path, get_state_dir())

    if session_id:
        try:
            from askr.session.registry import deregister_session
            deregister_session(session_id)
        except Exception:
            pass
        # Clear this session from the "already got a companion" set — it's gone
        # now, no point keeping it around (and it stops the set from growing
        # forever across every session that ever crossed the context trigger).
        try:
            from askr.session.lifecycle import _load_companioned_sessions, _save_companioned_sessions
            companioned = _load_companioned_sessions()
            if session_id in companioned:
                companioned.discard(session_id)
                _save_companioned_sessions(companioned)
        except Exception:
            pass
        # Prune the quota-warning dedup set of any reset window that's already
        # passed — it's keyed by quota_reset_at (account-wide window), not
        # session_id, so there's nothing session-specific to discard here;
        # this just stops the set from growing forever.
        try:
            from datetime import datetime, timezone
            from askr.session.lifecycle import _load_quota_warned_windows, _save_quota_warned_windows
            quota_warned = _load_quota_warned_windows()
            now = datetime.now(timezone.utc)
            still_valid = set()
            for reset_at in quota_warned:
                try:
                    if datetime.fromisoformat(reset_at.replace("Z", "+00:00")) > now:
                        still_valid.add(reset_at)
                except Exception:
                    continue
            if still_valid != quota_warned:
                _save_quota_warned_windows(still_valid)
        except Exception:
            pass

    # Always run the authoritative stop checkpoint first — this is ground truth.
    # _write_relaunch_notification_if_pending uses its result but never replaces it.
    from askr.session.checkpoint import create_checkpoint
    result = create_checkpoint(
        trigger_type="stop",
        developer=developer,
        transcript_path=transcript_path,
        session_id=session_id,
    )

    completed_goals = result.get("completed_goals", [])
    duration_seconds = result.get("duration_seconds", 0)

    # Authoritative "this turn is done" signal — checked by lifecycle.py before
    # opening a companion session, instead of guessing from JSONL idle time.
    _signal_turn_stopped(session_id)

    # If daemon flagged a pending checkpoint, write the re-launch notification now.
    # Return early so we don't also send a session-end card — the new session handles continuity.
    if _write_relaunch_notification_if_pending(result):
        _advance_launch_goal()
        return

    # Only send a card for meaningful stops — goals completed or session ran >5 min.
    # Suppresses noise from casual conversation turns and quick tests.
    if completed_goals or duration_seconds >= 300:
        _broadcast_session_end(developer, completed_goals, os.getcwd(), duration_seconds, autonomous)

    # Voice has its own gate (see _speak_session_done docstring) — independent
    # of the Discord card's total-session-duration gate above.
    _speak_session_done(completed_goals, transcript_path)

    _advance_launch_goal()


if __name__ == "__main__":
    main()
