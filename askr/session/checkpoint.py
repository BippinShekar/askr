#!/usr/bin/env python3
"""
Checkpoint Engine

Generates handover documentation, updates state files, and commits+pushes.
Called by stop.py (normal session end) and lifecycle.py (threshold triggers).

Handover is written by Haiku from the actual transcript — not from mechanical
parsing of file names and bash commands. The result is actionable context for
the next session to continue work without manual recovery.
"""

import os
import json
import subprocess
from datetime import datetime, timezone
from typing import Optional

_RESULT_PATH = os.path.expanduser("~/.config/askr/checkpoint_result.json")
_MAX_TRANSCRIPT_ENTRIES = 60  # enough to capture a substantial work session


# ---------------------------------------------------------------------------
# Transcript reading
# ---------------------------------------------------------------------------

def read_transcript(transcript_path: str) -> list:
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
    return entries[-_MAX_TRANSCRIPT_ENTRIES:]


def _extract_tool_actions(entries: list) -> list[str]:
    actions = []
    for entry in entries:
        msg = entry.get("message", {})
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            inp  = block.get("input", {})
            if name in ("Write", "Edit", "MultiEdit"):
                path = inp.get("file_path") or inp.get("path", "")
                if path:
                    actions.append(f"Modified {path}")
            elif name == "Bash":
                cmd = inp.get("command", "")[:80]
                if cmd:
                    actions.append(f"Ran: {cmd}")
    return actions


def _build_transcript_text(entries: list) -> str:
    """
    Flatten the transcript to a readable text format for the LLM.
    Includes user messages and assistant text+tool actions — skips hook payloads.
    """
    lines = []
    for entry in entries:
        msg  = entry.get("message", {})
        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", [])

        if role == "user":
            if isinstance(content, str) and len(content) > 5:
                lines.append(f"USER: {content[:400]}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text and len(text) > 5:
                            lines.append(f"USER: {text[:400]}")

        elif role == "assistant":
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text = block.get("text", "").strip()
                            if text:
                                lines.append(f"ASSISTANT: {text[:300]}")
                        elif block.get("type") == "tool_use":
                            name = block.get("name", "")
                            inp  = block.get("input", {})
                            if name in ("Write", "Edit", "MultiEdit"):
                                path = inp.get("file_path") or inp.get("path", "")
                                lines.append(f"TOOL: {name}({path})")
                            elif name == "Bash":
                                cmd = inp.get("command", "")[:80]
                                lines.append(f"TOOL: Bash({cmd})")
                            else:
                                lines.append(f"TOOL: {name}")
    return "\n".join(lines)


def _generate_handover_with_llm(transcript_text: str) -> Optional[str]:
    """
    Call Haiku to generate an action-ready handover from the transcript.
    The output is read by a Claude Code session, not a human — it must be
    specific enough to act on without any additional context.
    """
    if not transcript_text.strip():
        return None
    try:
        from askr.clients.claude import call_claude
        prompt = f"""A Claude Code session just ended. You are writing a handover document that the NEXT Claude Code session will read as its first instruction. It has no memory of this session. It needs to know exactly what to do and where — not a summary for a human.

SESSION TRANSCRIPT:
{transcript_text}

Write the handover in this exact format. No emojis. No markdown decorations. No boilerplate phrases like "continue from where we left off" or "check implementation_state.md". Every line must be concrete and immediately actionable.

Critical rules — read carefully before writing:
- FINAL STATE ONLY. The transcript may contain suggestions that were later reversed or superseded. Only the final settled conclusion counts. If an approach was raised and then explicitly rejected or decided against later in the same session, put it in Failed Approaches — never in Next Action.
- ANSWERED QUESTIONS ARE NOT OPEN. If a question was asked AND answered in the transcript, it is resolved. Do not list it in Open Questions. Open Questions are only for things that remain genuinely unresolved at session end.
- LAST EXCHANGE WINS. When the final exchange in the transcript contradicts or overrides an earlier one, the earlier one is irrelevant. The handover reflects where things ended up, not where they passed through.

Sessions vary in type — implementation, testing/debugging, exploration, or discussion. Adapt the Status section accordingly:
- Implementation session: list file paths and their current state
- Testing/debugging session: list what was tested, what passed/failed, what system state was confirmed
- Exploration/discussion session: list decisions made, options ruled out, direction agreed on

## Task
[One sentence: what was being worked on — could be implementing a feature, debugging a system, testing behavior, or making a design decision]

## Status
[Bullet list: concrete current state. For implementation: file paths and what changed. For testing: what was verified and what the outcome was. For debugging: what was found. Never write "Unknown" if the transcript contains relevant information — extract it.]

## Failed Approaches
[Bullet list of approaches that were tried and did not work OR were suggested and then rejected, with brief reason. Write "None" if none.]

## Next Action
[The single next thing to do — specific enough that Claude can start immediately. Must reflect the FINAL state of the session, not any intermediate suggestion that was later reversed. For testing sessions this might be "run X test" or "verify Y behavior". For implementation it's a file path and change. One action only.]

## Open Questions
[Bullet list of genuinely unresolved decisions or unknowns that were NOT answered during this session. If a question was raised and answered in the transcript, do not list it here. Write "None" if none.]

If a section truly has no information in the transcript, write "Unknown" — but exhaust the transcript first before concluding that."""

        return call_claude(
            "You write precise technical handover documents for autonomous AI coding agents. Output only the document — no preamble, no explanation.",
            prompt,
            mode="checkpoint",
            query_preview="handover generation",
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Fallback: mechanical summary when LLM is unavailable
# ---------------------------------------------------------------------------

def _build_fallback_summary(entries: list) -> tuple[str, list]:
    """
    Mechanical fallback when LLM is unavailable.
    Still avoids useless boilerplate — only writes what is actually known.
    """
    tool_actions = _extract_tool_actions(entries)
    user_prompts = []

    for entry in entries:
        msg = entry.get("message", {})
        if msg.get("role") != "user":
            continue
        content = msg.get("content", [])
        if isinstance(content, str) and len(content) > 5:
            user_prompts.append(content[:300])
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text and len(text) > 5:
                        user_prompts.append(text[:300])

    files_changed = sorted(set(
        a.replace("Modified ", "") for a in tool_actions if a.startswith("Modified")
    ))

    sections = []

    task = user_prompts[-1] if user_prompts else "Unknown — transcript unavailable"
    sections.append(f"## Task\n\n{task}")

    if files_changed:
        status_lines = "\n".join(f"- {f} — modified this session, verify state" for f in files_changed[:20])
        sections.append(f"## Status\n\n{status_lines}")
    else:
        sections.append("## Status\n\nUnknown — no file modifications found in transcript")

    sections.append("## Failed Approaches\n\nUnknown — LLM handover unavailable, review transcript manually")

    if files_changed:
        sections.append(f"## Next Action\n\nInspect {files_changed[-1]} — last file modified this session")
    else:
        sections.append("## Next Action\n\nUnknown — run `git diff HEAD~1` to see what changed last session")

    sections.append("## Open Questions\n\nUnknown")

    return "\n\n".join(sections), tool_actions


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def git_commit_push(state_dir: str, developer: str, trigger_type: str):
    try:
        subprocess.run(["git", "add", state_dir], capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain", state_dir],
            capture_output=True, text=True,
        )
        if not result.stdout.strip():
            return
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
        label = "checkpoint" if trigger_type in ("context", "quota", "manual") else trigger_type
        subprocess.run(
            ["git", "commit", "-m", f"askr: {label} [{developer}] {ts}"],
            capture_output=True,
        )
        subprocess.run(["git", "push", "--quiet"], capture_output=True, timeout=30)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main entry point
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
    """
    from askr.state.config import get_state_dir as _get_state_dir
    if state_dir is None:
        state_dir = _get_state_dir()

    entries = read_transcript(transcript_path)

    if trigger_type == "emergency":
        summary = (
            "## What Was Being Done\n\nEmergency checkpoint triggered.\n\n"
            "## Current State\n\n- Check implementation_state.md for what was in progress\n\n"
            "## Next Step\n\nReview recent git diff and implementation_state.md, then continue.\n\n"
            "## Blockers\n\nNone noted"
        )
        tool_actions = _extract_tool_actions(entries)
    else:
        # Try LLM-generated handover first; fall back to mechanical if unavailable
        transcript_text = _build_transcript_text(entries)
        llm_summary = _generate_handover_with_llm(transcript_text)
        if llm_summary:
            summary = llm_summary
            tool_actions = _extract_tool_actions(entries)
        else:
            summary, tool_actions = _build_fallback_summary(entries)

    from askr.state.writer import write_handover
    handover_path = write_handover(summary, developer)

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

    _notify_discord_checkpoint(trigger_type, developer, result)

    return result


def _notify_discord_checkpoint(trigger_type: str, developer: str, result: dict):
    try:
        from askr.clients.discord import send_message
        label = {
            "context": "Context limit",
            "quota":   "Quota limit",
            "manual":  "Manual checkpoint",
            "stop":    "Session ended",
            "emergency": "Emergency checkpoint",
        }.get(trigger_type, trigger_type.capitalize())
        ts = result.get("timestamp", "")[:16].replace("T", " ")
        msg = f"**[askr] {label}** — {developer} @ {ts} UTC\nState saved to git. Handover ready."
        send_message(msg)
    except Exception:
        pass
