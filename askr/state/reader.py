import os
import glob
from askr.state.config import load_developer, state_path


def _read(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return ""


def load_own_handover(developer: str = None) -> str:
    dev = developer or load_developer()
    return _read(state_path(f"handover_{dev}.md"))


def load_team_handovers(developer: str = None) -> str:
    dev = developer or load_developer()
    pattern = state_path("handover_*.md")
    parts = []
    for path in sorted(glob.glob(pattern)):
        filename = os.path.basename(path)
        other_dev = filename.replace("handover_", "").replace(".md", "")
        if other_dev == dev:
            continue
        content = _read(path)
        if content:
            parts.append(f"=== {other_dev} handover ===\n{content}")
    return "\n\n".join(parts)


def load_decisions(last_n: int = 20) -> str:
    path = state_path("decisions.md")
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        lines = [l.rstrip() for l in f if l.strip() and l.startswith("[")]
    return "\n".join(lines[-last_n:])


def load_architecture() -> str:
    return _read(state_path("architecture.md"))


def load_current_tasks() -> str:
    pattern = state_path("current_task_*.md")
    parts = []
    for path in sorted(glob.glob(pattern)):
        content = _read(path)
        if content:
            parts.append(content)
    return "\n\n".join(parts)


def load_blockers() -> str:
    return _read(state_path("blockers.md"))


def build_context_injection(developer: str = None) -> str:
    dev = developer or load_developer()

    own_handover = load_own_handover(dev)
    team_handovers = load_team_handovers(dev)
    decisions = load_decisions()
    architecture = load_architecture()
    current_tasks = load_current_tasks()
    blockers = load_blockers()

    sections = []

    if own_handover:
        sections.append(f"YOUR LAST SESSION HANDOVER:\n{own_handover}")

    if team_handovers:
        sections.append(f"TEAM HANDOVERS:\n{team_handovers}")

    if current_tasks:
        sections.append(f"CURRENT TASKS:\n{current_tasks}")

    if decisions:
        sections.append(f"RECENT DECISIONS:\n{decisions}")

    if architecture:
        sections.append(f"ARCHITECTURE:\n{architecture}")

    if blockers:
        sections.append(f"BLOCKERS:\n{blockers}")

    if not sections:
        return ""

    return "=== ASKR PROJECT STATE ===\n\n" + "\n\n---\n\n".join(sections) + "\n\n=== END STATE ==="
