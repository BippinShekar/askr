"""
Dangerous-permission detection for the cross-developer task queue.

A task queued into your session by a teammate (askr task queue) runs with
whatever permissions your session already has. Permissions you granted
yourself for your own work don't constitute authorization for someone
else's task — this module answers "is this session in a state where a
queued task would run with no friction at all," so session_start.py can
hold queued tasks for confirmation instead of auto-injecting them.

Three independent signals, any one is sufficient (roadmap.md Phase 5):
  1. --dangerously-skip-permissions in the running claude process's launch args
  2. Unrestricted Bash in .claude/settings.json allowedTools
  3. An rm/delete pattern in .claude/settings.local.json permissions.allow
"""

import json
import os
import re
import subprocess

_RM_PATTERN = re.compile(r"\brm\b|\brmdir\b|\bunlink\b")


def _claude_launch_args_dangerous(project_path: str) -> bool:
    """Check the running claude process(es) for this project's launch command.

    Mirrors the pgrep + lsof-cwd-match pattern session_start.py already uses
    to find "the claude process for this project" — reused here rather than
    invented fresh, since it's the only reliable way to see launch args from
    a hook subprocess (Claude Code's hook stdin payload doesn't include them).
    """
    try:
        pgrep = subprocess.run(
            ["pgrep", "-x", "claude"], capture_output=True, text=True, timeout=5,
        )
        for pid_str in pgrep.stdout.strip().splitlines():
            pid = pid_str.strip()
            if not pid:
                continue
            lsof = subprocess.run(
                ["lsof", "-a", "-p", pid, "-d", "cwd", "-F", "n"],
                capture_output=True, text=True, timeout=3,
            )
            matches_cwd = any(
                line.startswith("n") and line[1:] == project_path
                for line in lsof.stdout.splitlines()
            )
            if not matches_cwd:
                continue
            ps = subprocess.run(
                ["ps", "-o", "command=", "-p", pid],
                capture_output=True, text=True, timeout=3,
            )
            if "dangerously-skip-permissions" in ps.stdout:
                return True
    except Exception:
        pass
    return False


def _allowed_tools_unrestricted(project_path: str) -> bool:
    settings_path = os.path.join(project_path, ".claude", "settings.json")
    try:
        with open(settings_path) as f:
            allowed = json.load(f).get("allowedTools", [])
        return any(
            t == "Bash" or t.startswith("Bash(*") or t == "Bash(*)"
            for t in allowed
        )
    except Exception:
        return False


def _permissions_allow_has_delete(project_path: str) -> bool:
    local_path = os.path.join(project_path, ".claude", "settings.local.json")
    try:
        with open(local_path) as f:
            allow = json.load(f).get("permissions", {}).get("allow", [])
        return any(_RM_PATTERN.search(p) for p in allow)
    except Exception:
        return False


def is_dangerous_session(project_path: str) -> tuple[bool, list[str]]:
    """Returns (dangerous, reasons) — reasons is empty iff dangerous is False."""
    reasons = []
    if _claude_launch_args_dangerous(project_path):
        reasons.append("--dangerously-skip-permissions in session launch args")
    if _allowed_tools_unrestricted(project_path):
        reasons.append("unrestricted Bash in .claude/settings.json allowedTools")
    if _permissions_allow_has_delete(project_path):
        reasons.append("rm/delete pattern in .claude/settings.local.json permissions.allow")
    return (len(reasons) > 0, reasons)
