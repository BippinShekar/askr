import os
import re
import json as _json
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


def _handover_json_to_md(data: dict, developer: str = "") -> str:
    """Convert JSON handover to human-readable markdown (derived copy only)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    dev = developer or data.get("session_metadata", {}).get("developer", "")
    lines = [f"# Handover: {dev}\n\nLast updated: {ts}\n\n*Source of truth: `handover_{dev}.json`*\n"]

    if data.get("task"):
        lines.append(f"## Task\n{data['task']}")
    if data.get("discussion_summary"):
        lines.append(f"## Discussion\n{data['discussion_summary']}")
    if data.get("completion_pct") is not None:
        lines.append(f"## Progress\n{data['completion_pct']}% complete")
    if data.get("accomplishments"):
        items = [f"- {'✅' if a.get('done') else '🔲'} {a['what']}" for a in data["accomplishments"]]
        lines.append("## Accomplishments\n" + "\n".join(items))
    if data.get("in_progress"):
        items = [
            f"- `{ip['file']}`" + (f" (line {ip['last_line']})" if ip.get("last_line") else "") + f": {ip['what']}"
            for ip in data["in_progress"]
        ]
        lines.append("## In Progress\n" + "\n".join(items))
    if data.get("next_actions"):
        items = []
        for a in sorted(data["next_actions"], key=lambda x: x.get("order", 99)):
            why = f"\n   *Why: {a['why']}*" if a.get("why") else ""
            items.append(f"{a.get('order', '')}. {a['action']}{why}")
        lines.append("## Next Actions\n" + "\n".join(items))
    if data.get("decisions"):
        items = [
            f"- {d['decision']}" + (f" — {d['reason']}" if d.get("reason") else "")
            for d in data["decisions"]
        ]
        lines.append("## Decisions\n" + "\n".join(items))
    if data.get("user_rejected_decisions"):
        items = [
            f"- **{r['what_was_proposed']}** — \"{r.get('user_signal', '')}\" (domain: {r.get('domain', '')})"
            for r in data["user_rejected_decisions"]
        ]
        lines.append("## User-Rejected Approaches\n" + "\n".join(items))
    if data.get("failed_approaches"):
        items = [
            f"- {f['approach']}" + (f" — {f['reason']}" if f.get("reason") else "")
            for f in data["failed_approaches"]
        ]
        lines.append("## Failed Approaches\n" + "\n".join(items))
    if data.get("files_in_play"):
        lines.append("## Files In Play\n" + "\n".join(f"- `{f}`" for f in data["files_in_play"]))
    if data.get("relational_files"):
        items = [
            f"- `{r['file']}` ({r.get('relationship', 'related')}): {r.get('why', '')}"
            for r in data["relational_files"]
        ]
        lines.append("## Relational Files\n" + "\n".join(items))
    if data.get("uncommitted_files"):
        lines.append("## Uncommitted Files\n" + "\n".join(f"- `{f}`" for f in data["uncommitted_files"]))
    if data.get("blockers"):
        lines.append("## Blockers\n" + "\n".join(f"- {b}" for b in data["blockers"]))

    return "\n\n".join(lines) + "\n"


def write_handover(content, developer: str = None) -> str:
    dev = developer or load_developer()
    ensure_state_dir()

    if isinstance(content, dict):
        content.setdefault("session_metadata", {})["developer"] = dev

        json_path = state_path(f"handover_{dev}.json")
        with open(json_path, "w") as f:
            _json.dump(content, f, indent=2)

        md_path = state_path(f"handover_{dev}.md")
        with open(md_path, "w") as f:
            f.write(_handover_json_to_md(content, dev))

        return json_path
    else:
        # Fallback: legacy markdown path
        path = state_path(f"handover_{dev}.md")
        _write(path, f"# Handover: {dev}\n\nLast updated: {_now()}\n\n{str(content).strip()}\n")
        return path


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
