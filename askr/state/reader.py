import os
import glob
import json as _json
from askr.state.config import load_developer, state_path


def _read(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return ""


def _format_handover_for_context(data: dict) -> str:
    """Format JSON handover as a targeted, Claude-readable context string."""
    parts = []

    if data.get("task"):
        parts.append(f"## Task\n{data['task']}")
    if data.get("discussion_summary"):
        parts.append(f"## What Was Discussed\n{data['discussion_summary']}")
    if data.get("in_progress"):
        items = [
            f"- {ip['file']}" + (f" (line {ip['last_line']})" if ip.get("last_line") else "") + f": {ip['what']}"
            for ip in data["in_progress"]
        ]
        parts.append("## In Progress — pick up here\n" + "\n".join(items))
    if data.get("next_actions"):
        actions = sorted(data["next_actions"], key=lambda x: x.get("order", 99))
        items = [
            f"{a.get('order', i+1)}. {a['action']}" + (f" — {a['why']}" if a.get("why") else "")
            for i, a in enumerate(actions)
        ]
        parts.append("## Next Actions (in order)\n" + "\n".join(items))
    if data.get("user_rejected_decisions"):
        items = [
            f"- DO NOT propose: {r['what_was_proposed']} (domain: {r.get('domain', 'general')})"
            for r in data["user_rejected_decisions"]
            if r.get("confidence", 0) >= 0.7
        ]
        if items:
            parts.append("## User Has Rejected These — do not re-propose\n" + "\n".join(items))
    if data.get("decisions"):
        items = [f"- {d['decision']}" for d in data["decisions"]]
        parts.append("## Settled Decisions\n" + "\n".join(items))
    if data.get("failed_approaches"):
        items = [f"- {f['approach']}: {f.get('reason', '')}" for f in data["failed_approaches"]]
        parts.append("## Failed Approaches\n" + "\n".join(items))
    if data.get("uncommitted_files"):
        parts.append(
            "## Uncommitted Files (in-flight — do not re-implement)\n"
            + "\n".join(f"- {f}" for f in data["uncommitted_files"])
        )
    if data.get("blockers"):
        parts.append("## Blockers\n" + "\n".join(f"- {b}" for b in data["blockers"]))
    if data.get("files_in_play"):
        parts.append("## Files In Play\n" + "\n".join(f"- {f}" for f in data["files_in_play"]))
    if data.get("relational_files"):
        items = [
            f"- {r['file']} ({r.get('relationship', '')}): {r.get('why', '')}"
            for r in data["relational_files"]
        ]
        parts.append("## Related Files\n" + "\n".join(items))

    return "\n\n".join(parts)


def load_own_handover(developer: str = None) -> str:
    dev = developer or load_developer()

    # JSON first (Phase 3.11+)
    json_path = state_path(f"handover_{dev}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                data = _json.load(f)
            return _format_handover_for_context(data)
        except Exception:
            pass

    # Fallback: legacy .md
    return _read(state_path(f"handover_{dev}.md"))


def load_own_handover_raw(developer: str = None) -> dict | str:
    """Return raw handover data — dict if JSON exists, str if only .md."""
    dev = developer or load_developer()
    json_path = state_path(f"handover_{dev}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                return _json.load(f)
        except Exception:
            pass
    return _read(state_path(f"handover_{dev}.md"))


def load_team_handovers(developer: str = None) -> str:
    dev = developer or load_developer()
    parts = []

    for path in sorted(glob.glob(state_path("handover_*.json"))):
        other_dev = os.path.basename(path).replace("handover_", "").replace(".json", "")
        if other_dev == dev:
            continue
        try:
            with open(path) as f:
                data = _json.load(f)
            parts.append(f"=== {other_dev} handover ===\n{_format_handover_for_context(data)}")
        except Exception:
            pass

    # Also pick up any .md-only handovers (legacy / other devs not yet on 3.11)
    for path in sorted(glob.glob(state_path("handover_*.md"))):
        other_dev = os.path.basename(path).replace("handover_", "").replace(".md", "")
        if other_dev == dev:
            continue
        json_path = state_path(f"handover_{other_dev}.json")
        if os.path.exists(json_path):
            continue  # already loaded above
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


def load_blockers() -> str:
    return _read(state_path("blockers.md"))


def build_context_injection(developer: str = None) -> str:
    dev = developer or load_developer()

    own_handover = load_own_handover(dev)
    team_handovers = load_team_handovers(dev)
    decisions = load_decisions()
    architecture = load_architecture()
    blockers = load_blockers()

    sections = []

    if own_handover:
        sections.append(f"YOUR LAST SESSION HANDOVER:\n{own_handover}")
    if team_handovers:
        sections.append(f"TEAM HANDOVERS:\n{team_handovers}")
    if decisions:
        sections.append(f"RECENT DECISIONS:\n{decisions}")
    if architecture:
        sections.append(f"ARCHITECTURE:\n{architecture}")
    if blockers:
        sections.append(f"UNIVERSAL BLOCKERS (affect whole team):\n{blockers}")

    if not sections:
        return ""

    return "=== ASKR PROJECT STATE ===\n\n" + "\n\n---\n\n".join(sections) + "\n\n=== END STATE ==="
