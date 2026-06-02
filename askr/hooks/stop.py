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

from askr.state.config import STATE_DIR, load_developer


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

        if role == "user":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    pass
                elif isinstance(block, str) and len(block) > 5:
                    user_prompts.append(block[:100])

        if role == "assistant":
            for block in msg.get("content", []):
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    name = block.get("name", "")
                    inp = block.get("input", {})
                    if name in ("Write", "Edit"):
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

    return "\n\n".join(sections)


def _git_commit_push(developer: str):
    try:
        subprocess.run(["git", "add", STATE_DIR], capture_output=True)
        result = subprocess.run(
            ["git", "status", "--porcelain", STATE_DIR],
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

    if not os.path.isdir(STATE_DIR):
        return

    developer = load_developer()
    transcript_path = payload.get("transcript_path", "")
    entries = _read_transcript(transcript_path)

    summary = _summarize_session(entries, developer)

    from askr.state.writer import write_handover
    write_handover(summary, developer)

    _git_commit_push(developer)


if __name__ == "__main__":
    main()
