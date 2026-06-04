#!/usr/bin/env python3
"""
Phase 2 - Checkpoint Engine

Generates handover documentation, updates state files, and commits+pushes.
Called by both stop.py (normal session end) and lifecycle.py (threshold triggers).

Writes ~/.config/askr/checkpoint_result.json so the lifecycle daemon knows
the checkpoint succeeded and can proceed with the session transition.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from typing import Optional

_RESULT_PATH = os.path.expanduser("~/.config/askr/checkpoint_result.json")


# ---------------------------------------------------------------------------
# Transcript helpers (shared with stop.py)
# ---------------------------------------------------------------------------

def read_transcript(transcript_path: str, max_entries: int = 40) -> list:
    if not transcript_path or not os.path.exists(transcript_path):
        return []
    entries = []
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries[-max_entries:]


def build_handover_summary(transcript_entries: list) -> tuple:
    """
    Returns (summary_markdown: str, tool_actions: list[str]).
    Shared between stop.py and checkpoint.py.
    """
    tool_actions = []
    user_prompts = []

    for entry in transcript_entries:
        msg = entry.get("message", {})
        role = msg.get("role", "")
        content = msg.get("content", [])

        if role == "user":
            if isinstance(content, str) and len(content) > 5:
                user_prompts.append(content[:150])
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text and len(text) > 5:
                            user_prompts.append(text[:150])

        if role == "assistant":
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        inp = block.get("input", {})
                        if name in ("Write", "Edit", "MultiEdit"):
                            path = inp.get("file_path") or inp.get("path", "")
                            if path:
                                tool_actions.append(f"Modified {path}")
                        elif name == "Bash":
                            cmd = inp.get("command", "")[:60]
                            if cmd:
                                tool_actions.append(f"Ran: {cmd}")

    files_changed = sorted(set(
        a.replace("Modified ", "") for a in tool_actions if a.startswith("Modified")
    ))

    sections = []

    if user_prompts:
        sections.append(f"## Objective\n\n{user_prompts[-1]}")

    sections.append("## Next Step\n\n[Continue from where this session left off - check files changed below]")

    if tool_actions:
        completed = "\n".join(f"- {a}" for a in tool_actions[-20:])
        sections.append(f"## Completed This Session\n\n{completed}")

    if files_changed:
        files = "\n".join(f"- {f}" for f in files_changed[:20])
        sections.append(f"## Files Changed\n\n{files}")

    sections.append("## Decisions Made\n\n[Check decisions.md]")
    sections.append("## Tests\n\nUnknown - check last Bash output")
    sections.append("## Blockers\n\nNone noted")

    return "\n\n".join(sections), tool_actions


def git_commit_push(state_dir: str, developer: str, trigger_type: str):
    try:
        subprocess.run(["git", "add", state_dir], capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain", state_dir],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        label = "checkpoint" if trigger_type in ("context", "quota", "manual") else trigger_type
        subprocess.run(
            ["git", "commit", "-m", f"askr: {label} [{developer}] {ts}"],
            capture_output=True
        )
        subprocess.run(["git", "push", "--quiet"], capture_output=True, timeout=30)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main checkpoint entry point
# ---------------------------------------------------------------------------

def create_checkpoint(
    trigger_type: str,
    developer: str,
    transcript_path: str = "",
    state_dir: Optional[str] = None,
) -> dict:
    """
    Generate handover, update state files, commit and push.

    trigger_type: "context", "quota", "manual", "emergency", "stop"
    Returns result dict written to _RESULT_PATH.
    """
    from askr.state.config import get_state_dir as _get_state_dir
    if state_dir is None:
        state_dir = _get_state_dir()

    entries = read_transcript(transcript_path)
    summary, tool_actions = build_handover_summary(entries)

    if trigger_type == "emergency":
        summary = (
            f"## Objective\n\nEmergency checkpoint - triggered by {trigger_type}.\n\n"
            f"## Next Step\n\nReview recent work and continue from last known state.\n\n"
            f"## Context\n\nCheck implementation_state.md for what was in progress."
        )

    from askr.state.writer import write_handover
    handover_path = write_handover(summary, developer)

    # Infer goal completions
    try:
        from askr.state.goals import load_today_goals, infer_completed_from_activity, complete_goal
        goals = load_today_goals()
        if goals and tool_actions:
            completed = infer_completed_from_activity(tool_actions, goals)
            for g in completed:
                complete_goal(g)
    except Exception:
        pass

    git_commit_push(state_dir, developer, trigger_type)

    result = {
        "trigger": trigger_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "handover_path": handover_path or "",
        "developer": developer,
    }

    try:
        os.makedirs(os.path.dirname(_RESULT_PATH), exist_ok=True)
        with open(_RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result
