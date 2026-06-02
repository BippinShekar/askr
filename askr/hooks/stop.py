#!/usr/bin/env python3
"""
Claude Code Hook - Stop

Fires when a Claude Code session ends.
Generates handover.md from the session transcript, commits state, pushes.
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.config import get_state_dir, load_developer


def _read_transcript(transcript_path: str, max_entries: int = 40) -> list[dict]:
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


def _summarize_session(transcript_entries: list[dict], developer: str) -> str:
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
        last_objective = user_prompts[-1]
        sections.append(f"## Objective\n\n{last_objective}")

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


def _infer_and_update_goals(tool_actions: list[str]):
    try:
        from askr.state.goals import load_today_goals, infer_completed_from_activity, complete_goal
        goals = load_today_goals()
        if not goals or not tool_actions:
            return
        completed = infer_completed_from_activity(tool_actions, goals)
        for g in completed:
            complete_goal(g)
    except Exception:
        pass


def _git_commit_push(developer: str):
    try:
        subprocess.run(["git", "add", get_state_dir()], capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain", get_state_dir()],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            return

        from datetime import datetime
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        subprocess.run(
            ["git", "commit", "-m", f"askr: checkpoint [{developer}] {ts}"],
            capture_output=True
        )
        subprocess.run(["git", "push", "--quiet"], capture_output=True, timeout=30)
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if not os.path.isdir(get_state_dir()):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")
    entries = _read_transcript(transcript_path)

    summary, tool_actions = _summarize_session(entries, developer)

    from askr.state.writer import write_handover
    write_handover(summary, developer)

    _infer_and_update_goals(tool_actions)

    _git_commit_push(developer)


if __name__ == "__main__":
    main()
