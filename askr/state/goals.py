import os
import json
import uuid
from datetime import datetime, date, timezone
from askr.state.config import state_path, ensure_state_dir
from askr.state.writer import file_lock

GOALS_FILE = "goals.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return date.today().strftime("%Y-%m-%d")


def _path(state_dir: str = None) -> str:
    return os.path.join(state_dir, GOALS_FILE) if state_dir else state_path(GOALS_FILE)


def _read_all(state_dir: str = None) -> list[dict]:
    """Read goals from JSONL. Last entry per ID wins (append-only update pattern)."""
    p = _path(state_dir)
    if not os.path.exists(p):
        return []
    by_id: dict[str, dict] = {}
    with open(p) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                eid = entry.get("id")
                if eid:
                    by_id[eid] = entry
            except Exception:
                pass
    return list(by_id.values())


def _append(entry: dict, state_dir: str = None):
    path = _path(state_dir)
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)
    else:
        ensure_state_dir()
    with file_lock(path):
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")


def add_goal(text: str, section: str = "today", auto_suggested: bool = False):
    _append({
        "id":            uuid.uuid4().hex[:8],
        "text":          text.strip(),
        "status":        "open" if section == "today" else "backlog",
        "date":          _today(),
        "added":         _now_iso(),
        "auto_suggested": auto_suggested,
        "done_at":       None,
    })


def complete_goal(text: str, state_dir: str = None) -> bool:
    for g in _read_all(state_dir):
        if g.get("text", "").strip() == text.strip() and g.get("status") in ("open", "backlog"):
            _append({**g, "status": "done", "done_at": _now_iso()}, state_dir)
            return True
    return False


def discard_goal(text: str) -> bool:
    for g in _read_all():
        if g.get("text", "").strip() == text.strip() and g.get("status") in ("open", "backlog"):
            _append({**g, "status": "discarded", "done_at": _now_iso()})
            return True
    return False


def load_open_goals(state_dir: str = None) -> list[str]:
    return [g["text"] for g in _read_all(state_dir) if g.get("status") in ("open", "backlog")]


def load_today_goals(state_dir: str = None) -> list[str]:
    today = _today()
    return [
        g["text"] for g in _read_all(state_dir)
        if g.get("status") == "open" and g.get("date") == today
    ]


def get_stale_goals(hours: int = 6) -> list[tuple[str, str, float]]:
    now = datetime.now(timezone.utc)
    stale = []
    for g in _read_all():
        if g.get("status") not in ("open", "backlog"):
            continue
        added_str = g.get("added", "")
        if not added_str:
            continue
        try:
            added = datetime.fromisoformat(added_str.replace("Z", "+00:00"))
            age_hours = (now - added).total_seconds() / 3600
            if age_hours >= hours:
                stale.append((g["text"], added_str, round(age_hours, 1)))
        except Exception:
            continue
    return stale


def expire_auto_suggested_goals(state_dir: str = None) -> int:
    count = 0
    for g in _read_all(state_dir):
        if g.get("auto_suggested") and g.get("status") in ("open", "backlog"):
            _append({**g, "status": "discarded", "done_at": _now_iso()}, state_dir)
            count += 1
    return count


def load_done_today() -> list[str]:
    today = _today()
    return [
        g["text"] for g in _read_all()
        if g.get("status") == "done" and (g.get("done_at") or "")[:10] == today
    ]


def format_for_context() -> str:
    today_goals = load_today_goals()
    open_goals  = load_open_goals()
    backlog     = [g for g in open_goals if g not in today_goals]

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


def archive_stale_goals() -> int:
    today = _today()
    count = 0
    for g in _read_all():
        if g.get("status") == "open" and g.get("date") != today:
            _append({**g, "status": "backlog"})
            count += 1
    return count


def suggest_goals_from_handover(developer: str) -> list[str]:
    """
    Call Haiku to extract 1-2 suggested goals from the developer's last handover.
    Tries JSON handover first, then .md fallback.
    Returns [] if handover is missing, empty, or the Haiku call fails.
    """
    try:
        from askr.state.config import state_path as _state_path

        handover = ""
        json_path = _state_path(f"handover_{developer}.json")
        md_path   = _state_path(f"handover_{developer}.md")

        if os.path.exists(json_path):
            try:
                with open(json_path) as f:
                    data = json.load(f)
                parts = []
                if data.get("task"):
                    parts.append(f"Task: {data['task']}")
                if data.get("next_actions"):
                    actions = [a.get("action", "") for a in data["next_actions"][:3]]
                    parts.append("Next: " + "; ".join(actions))
                if data.get("in_progress"):
                    files = [ip.get("file", "") for ip in data["in_progress"][:3]]
                    parts.append("In progress: " + ", ".join(files))
                handover = "\n".join(parts)
            except Exception:
                pass
        elif os.path.exists(md_path):
            with open(md_path) as f:
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

    except Exception as e:
        from askr.utils.logger import log_error
        log_error("goals.suggest_goals_from_handover", str(e))
        return []


def infer_completed_from_activity(activity_lines: list[str], goals: list[str]) -> list[str]:
    """Use LLM to infer which goals were completed based on session activity."""
    if not goals or not activity_lines:
        return []
    try:
        from askr.clients.claude import call_claude
        import json as _json

        goals_text   = "\n".join(f"- {g}" for g in goals)
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

        completed = _json.loads(result)
        return [g for g in completed if g in goals]

    except Exception as e:
        from askr.utils.logger import log_error
        log_error("goals.infer_completed_from_activity", str(e))
        return []
