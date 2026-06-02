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
from askr.state.config import STATE_DIR


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

    if os.path.isdir(STATE_DIR):
        git_pull()

    context = build_context_injection()

    if context:
        print(json.dumps({"context": context}))
    else:
        print(json.dumps({}))


if __name__ == "__main__":
    main()
