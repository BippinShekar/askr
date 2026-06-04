#!/usr/bin/env python3
"""
Phase 2 - Safe Pause Engine

Determines whether it is safe to interrupt the current session and checkpoint.

SAFE:   tool idle, git clean, no test runners active
UNSAFE: active file writes in project, tests running, deploy/migration in progress
"""

import os
import re
import subprocess
from typing import Tuple

# Matches actual write-mode file descriptors: "1w", "2W", "10u" (read+write).
# Excludes: "cwd", "txt", "mem", "rtd" etc. which contain "w" but aren't write handles.
_WRITE_FD_RE = re.compile(r'^\d+[wWu]$')

# IDE / editor processes that legitimately hold write handles on project files.
# Their presence does NOT mean a file is being actively modified — the editor
# just keeps handles open. Exclude them from the lsof write-handle check.
_EDITOR_PROCESS_NAMES = {
    "cursor", "code", "code-oss", "code-insiders",
    "electron", "node",
    "webstorm", "intellij", "idea", "pycharm", "goland", "clion",
    "vim", "nvim", "emacs",
}

_TEST_PROCESS_NAMES = [
    "pytest", "py.test",
    "jest", "vitest",
    "go test",
    "npm test", "yarn test", "pnpm test",
    "rspec", "minitest",
    "cargo test",
    "mocha",
    "gradle test", "mvn test",
]

_DEPLOY_PROCESS_NAMES = [
    "terraform", "kubectl apply",
    "ansible-playbook",
    "docker build",
    "alembic upgrade", "db:migrate",
]


def _git_is_clean(project_path: str) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            ["git", "-C", project_path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return True, ""  # not a git repo or error - don't block on this
        dirty = result.stdout.strip()
        if dirty:
            changed_count = len(dirty.splitlines())
            return False, f"{changed_count} uncommitted file(s)"
        return True, ""
    except Exception:
        return True, ""


def _get_process_list() -> str:
    try:
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        return result.stdout
    except Exception:
        return ""


def _active_process_check(proc_list: str) -> Tuple[bool, str]:
    for name in _TEST_PROCESS_NAMES:
        if name in proc_list:
            return False, f"test runner active: {name}"
    for name in _DEPLOY_PROCESS_NAMES:
        if name in proc_list:
            return False, f"deploy/migration active: {name}"
    return True, ""


def _no_active_writes(project_path: str) -> Tuple[bool, str]:
    """Check for processes holding write locks on files in the project."""
    try:
        result = subprocess.run(
            ["lsof", "+D", project_path, "-w"],
            capture_output=True, text=True, timeout=5
        )
        lines = [l for l in result.stdout.splitlines() if l]
        write_lines = []
        for l in lines[1:]:
            parts = l.split()
            if len(parts) <= 4:
                continue
            # only flag actual write-mode FDs (e.g. "1w", "2W", "10u")
            # "cwd", "txt", "mem" etc. contain 'w' but are not write handles
            if not _WRITE_FD_RE.match(parts[3]):
                continue
            # skip IDE/editor processes — they legitimately hold write handles
            process_name = parts[0].lower()
            if any(editor in process_name for editor in _EDITOR_PROCESS_NAMES):
                continue
            write_lines.append(l)
        if write_lines:
            return False, f"active file write in project ({len(write_lines)} handle(s))"
        return True, ""
    except Exception:
        return True, ""  # lsof unavailable - don't block


def is_safe_to_pause(project_path: str) -> Tuple[bool, str]:
    """
    Returns (True, "") if safe to checkpoint now.
    Returns (False, reason) if unsafe.

    Note: git cleanliness is intentionally NOT checked. Uncommitted code
    changes are normal — Claude writes incrementally. The checkpoint commits
    only askr_state/, not source files. Blocking on uncommitted files would
    mean the checkpoint almost never fires.
    """
    procs = _get_process_list()
    ok, reason = _active_process_check(procs)
    if not ok:
        return False, reason

    ok, reason = _no_active_writes(project_path)
    if not ok:
        return False, reason

    return True, ""
