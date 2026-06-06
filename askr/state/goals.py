import os
import re
from datetime import datetime, date
from askr.state.config import state_path, ensure_state_dir

GOALS_FILE = "goals.md"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _read() -> str:
    path = state_path(GOALS_FILE)
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()


def _write(content: str):
    ensure_state_dir()
    with open(state_path(GOALS_FILE), "w") as f:
        f.write(content)


def _today_header() -> str:
    return f"## Today - {_today()}"


def _section_lines(content: str, header: str) -> list[str]:
    if header not in content:
        return []
    start = content.index(header) + len(header)
    rest = content[start:]
    end = rest.find("\n## ")
    section = rest[:end] if end > 0 else rest
    return [l.strip() for l in section.split("\n") if l.strip()]


def add_goal(text: str, section: str = "today"):
    content = _read()
    today_hdr = _today_header()
    new_line = f"- [ ] {text.strip()}"

    if not content:
        _write(
            f"# Goals\n\n{today_hdr}\n\n{new_line}\n\n"
            f"## Backlog\n\n## Done\n\n"
        )
        return

    target = today_hdr if section == "today" else "## Backlog"

    if target in content:
        idx = content.index(target) + len(target)
        content = content[:idx] + f"\n\n{new_line}" + content[idx:]
    elif section == "today":
        content = f"{today_hdr}\n\n{new_line}\n\n" + content
    else:
        content = content.rstrip() + f"\n\n## Backlog\n\n{new_line}\n"

    _write(content)


def complete_goal(text: str) -> bool:
    content = _read()
    if not content:
        return False

    patterns = [f"- [ ] {text.strip()}", f"- [x] {text.strip()}"]
    matched = None
    for p in patterns:
        if p in content:
            matched = p
            break

    if not matched:
        return False

    content = content.replace(matched + "\n", "").replace(matched, "")

    done_line = f"[{_now()}] {text.strip()}"
    if "## Done" in content:
        content = content.replace("## Done\n", f"## Done\n{done_line}\n", 1)
    else:
        content = content.rstrip() + f"\n\n## Done\n{done_line}\n"

    _write(content)
    return True


def load_open_goals() -> list[str]:
    content = _read()
    if not content:
        return []
    return [
        l.strip()[5:].strip()
        for l in content.split("\n")
        if l.strip().startswith("- [ ]")
    ]


def load_today_goals() -> list[str]:
    content = _read()
    if not content:
        return []
    lines = _section_lines(content, _today_header())
    return [l[5:].strip() for l in lines if l.startswith("- [ ]")]


def load_done_today() -> list[str]:
    content = _read()
    if not content:
        return []
    today = _today()
    lines = _section_lines(content, "## Done")
    return [l for l in lines if l.startswith(f"[{today}")]


def format_for_context() -> str:
    today_goals = load_today_goals()
    open_goals = load_open_goals()
    backlog = [g for g in open_goals if g not in today_goals]

    if not open_goals:
        return ""

    parts = ["TODAY'S GOALS:"]
    if today_goals:
        for g in today_goals:
            parts.append(f"  - [ ] {g}")
    else:
        parts.append('  [none set - add with: askr goal add "..."]')

    if backlog:
        parts.append("\nBACKLOG (top 3):")
        for g in backlog[:3]:
            parts.append(f"  - [ ] {g}")

    return "\n".join(parts)


def suggest_goals_from_handover(developer: str) -> list[str]:
    """
    Call Haiku to extract 1-2 suggested goals from the developer's last handover.
    Only called when today has no goals set. Returns [] if handover is missing,
    empty, or the Haiku call fails — so session start is never blocked.
    """
    try:
        from askr.state.config import state_path as _state_path
        handover_path = _state_path(f"handover_{developer}.md")
        if not os.path.exists(handover_path):
            return []

        with open(handover_path) as f:
            handover = f.read().strip()

        if len(handover) < 50:
            return []

        from askr.clients.claude import call_claude
        import json as _json

        prompt = f"""A developer's last Claude Code session ended with this handover:

{handover[:2000]}

Suggest 1-2 specific, actionable goals for their next session based on the Next Step and what was left in progress.

Reply with a JSON array of short goal strings (under 80 chars each). Be concrete.
Example: ["Complete lifecycle daemon sleep/resume logic", "Add quota reset timestamp parsing"]
If the handover is empty or unclear, return []."""

        result = call_claude(
            "You extract actionable goals from session handovers. Reply with valid JSON only.",
            prompt,
            mode="default",
            query_preview="goal suggestion from handover"
        )

        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        suggested = _json.loads(result)
        if not isinstance(suggested, list):
            return []
        return [str(g).strip()[:80] for g in suggested[:2] if g and str(g).strip()]

    except Exception:
        return []


def archive_stale_goals() -> int:
    """
    Move uncompleted goals from past-dated Today sections to Backlog.
    Called at every session start — prevents stale goals from driving new sessions.
    Returns count of goals archived.
    """
    content = _read()
    if not content:
        return 0

    today = _today()
    lines = content.split('\n')
    result_lines = []
    stale_goals = []
    in_stale = False

    for line in lines:
        m = re.match(r'^## Today - (\d{4}-\d{2}-\d{2})$', line.strip())
        if m:
            if m.group(1) != today:
                in_stale = True
                continue  # drop the stale header
            else:
                in_stale = False
        elif line.strip().startswith('## '):
            in_stale = False

        if in_stale:
            if line.strip().startswith('- [ ]'):
                stale_goals.append(line.strip())
            continue  # drop all lines in stale section

        result_lines.append(line)

    if not stale_goals:
        return 0

    content = '\n'.join(result_lines)
    insert = '\n'.join(stale_goals) + '\n'
    if '## Backlog' in content:
        content = content.replace('## Backlog\n', f'## Backlog\n{insert}', 1)
    else:
        content = content.rstrip() + '\n\n## Backlog\n\n' + insert

    _write(content)
    return len(stale_goals)


def infer_completed_from_activity(activity_lines: list[str], goals: list[str]) -> list[str]:
    """
    Use LLM to infer which goals were completed based on session activity.
    Returns list of goal texts that appear to be done.
    """
    if not goals or not activity_lines:
        return []

    try:
        from askr.clients.claude import call_claude

        goals_text = "\n".join(f"- {g}" for g in goals)
        activity_text = "\n".join(activity_lines[:30])

        prompt = f"""These were the open goals:
{goals_text}

This is what was done in the session:
{activity_text}

Which goals were clearly completed based on the activity? Reply with a JSON array of the exact goal strings that are done, or [] if none.
Only include goals where the activity clearly shows completion. Be conservative."""

        result = call_claude(
            "You analyze work logs against goals. Reply with valid JSON only.",
            prompt,
            mode="default",
            query_preview="goal completion inference"
        )

        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        import json
        completed = json.loads(result)
        return [g for g in completed if g in goals]

    except Exception:
        return []
