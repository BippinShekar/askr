#!/usr/bin/env python3
"""
Claude Code Hook - SessionStart

Fires at the start of every Claude Code session.
Pulls latest state from git, then injects project context.
"""

import sys
import os
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from askr.state.reader import build_context_injection
from askr.state.goals import format_for_context as goals_context
from askr.state.config import get_state_dir


def git_pull():
    try:
        subprocess.run(
            ["git", "pull", "--quiet"],
            capture_output=True,
            timeout=15
        )
    except Exception:
        pass


def main():
    try:
        payload = json.loads(sys.stdin.read())
    except Exception:
        payload = {}

    if os.path.isdir(get_state_dir()):
        git_pull()

    state_context = build_context_injection()
    goals = goals_context()

    parts = []
    if state_context:
        parts.append(state_context)
    if goals:
        parts.append(goals)

    if parts:
        print(json.dumps({"context": "\n\n".join(parts)}))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
