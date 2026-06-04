#!/usr/bin/env python3
"""
Phase 2 - Safe Pause Engine

Determines whether it is safe to interrupt the current session and checkpoint.

SAFE:   tool idle, git clean, no test runners active
UNSAFE: active file writes in project, tests running, deploy/migration in progress
"""

import os
import subprocess
from typing import Tuple

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
        # filter to write-mode open files (mode contains 'w' or 'W')
        write_lines = [l for l in lines[1:] if len(l.split()) > 4 and "w" in l.split()[3].lower()]
        if write_lines:
            return False, f"active file write in project ({len(write_lines)} handle(s))"
        return True, ""
    except Exception:
        return True, ""  # lsof unavailable - don't block


def is_safe_to_pause(project_path: str) -> Tuple[bool, str]:
    """
    Returns (True, "") if safe to checkpoint now.
    Returns (False, reason) if unsafe.
    """
    clean, reason = _git_is_clean(project_path)
    if not clean:
        return False, reason

    procs = _get_process_list()
    ok, reason = _active_process_check(procs)
    if not ok:
        return False, reason

    ok, reason = _no_active_writes(project_path)
    if not ok:
        return False, reason

    return True, ""
