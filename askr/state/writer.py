import os
import re
from datetime import datetime
from askr.state.config import load_developer, state_path, ensure_state_dir


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _read(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def _write(path: str, content: str):
    ensure_state_dir()
    with open(path, "w") as f:
        f.write(content)


def write_handover(content: str, developer: str = None):
    dev = developer or load_developer()
    path = state_path(f"handover_{dev}.md")
    _write(path, f"# Handover: {dev}\n\nLast updated: {_now()}\n\n{content.strip()}\n")


def write_current_task(objective: str, developer: str = None):
    dev = developer or load_developer()
    path = state_path(f"current_task_{dev}.md")
    _write(path, f"# Current Task: {dev}\n\nLast updated: {_now()}\n\n## Objective\n\n{objective.strip()}\n")


def append_decision(decision: str, reason: str = "", developer: str = None):
    dev = developer or load_developer()
    path = state_path("decisions.md")
    ensure_state_dir()

    line = f"[{_now()}] [{dev}] {decision.strip()}"
    if reason:
        line += f". Reason: {reason.strip()}"

    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("# Decisions\n\nAppend-only. One line per decision.\n\n")

    with open(path, "a") as f:
        f.write(line + "\n")


def update_implementation_section(content: str, developer: str = None):
    dev = developer or load_developer()
    path = state_path("implementation_state.md")
    ensure_state_dir()

    section_start = f"<!-- section:{dev} -->"
    section_end = f"<!-- /section:{dev} -->"
    new_section = f"{section_start}\n## {dev}\n\nLast active: {_now()}\n\n{content.strip()}\n{section_end}"

    existing = _read(path)

    if section_start in existing:
        updated = re.sub(
            rf"{re.escape(section_start)}.*?{re.escape(section_end)}",
            new_section,
            existing,
            flags=re.DOTALL
        )
        _write(path, updated)
    else:
        if not existing:
            header = "# Implementation State\n\nEach developer owns their section.\n\n"
            _write(path, header + new_section + "\n")
        else:
            with open(path, "a") as f:
                f.write("\n" + new_section + "\n")


def update_architecture(content: str):
    path = state_path("architecture.md")
    _write(path, f"# Architecture\n\nLast updated: {_now()}\n\n{content.strip()}\n")


def update_blockers(content: str):
    path = state_path("blockers.md")
    _write(path, f"# Blockers\n\nLast updated: {_now()}\n\n{content.strip()}\n")
