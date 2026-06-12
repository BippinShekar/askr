#!/usr/bin/env python3
"""
Implementation Guard Engine

Called when PreToolUse detects a significant write operation.
Loads architecture.md + handover + recent decisions, then calls Haiku
to cross-check the proposed change for architectural contradictions.

Returns a structured result: clean, or a list of specific issues.
"""

import os
import json
from datetime import datetime, timezone
from typing import Optional

_GUARD_TRIGGER_PATH = os.path.expanduser("~/.config/askr/guard_trigger.json")
_GUARD_RESULT_PATH  = os.path.expanduser("~/.config/askr/guard_result.json")


def _read(path: str, limit: int = 2000) -> str:
    try:
        if not os.path.exists(path):
            return ""
        with open(path) as f:
            return f.read()[:limit]
    except Exception:
        return ""


def _load_context(developer: str, state_dir: str) -> dict:
    return {
        "architecture":      _read(os.path.join(state_dir, "architecture.md")),
        "handover":          _read(os.path.join(state_dir, f"handover_{developer}.md")),
        "decisions":         _read(os.path.join(state_dir, "decisions.md"), limit=1500),
        "failed_approaches": _read(os.path.join(state_dir, "failed_approaches.md"), limit=1500),
    }


def run_guard_check(trigger: dict, developer: str, state_dir: str) -> dict:
    """
    Cross-check the triggered change against architecture context.
    Returns {"clean": True} or {"clean": False, "issues": [...], "summary": str}
    """
    context = _load_context(developer, state_dir)

    if not any(context.values()):
        return {"clean": True, "reason": "no architecture context available"}

    reason    = trigger.get("reason", "")
    tool      = trigger.get("tool", "")
    file_path = trigger.get("file_path", "")

    reason_label = {
        "new_file":        f"Claude is creating a new file: {file_path}",
        "batch_writes":    f"Claude has made multiple file edits this session (batch implementation detected). Latest: {file_path}",
        "shared_interface": f"Claude is editing a shared/core interface: {file_path}",
    }.get(reason, f"Claude is modifying: {file_path}")

    prompt = f"""An AI coding agent is about to make a significant change to a codebase. Your job is to check whether this change contradicts the known architecture, repeats a previously-rejected approach, or conflicts with settled decisions.

TRIGGER:
{reason_label}

ARCHITECTURE:
{context['architecture'] or 'Not available.'}

SETTLED DECISIONS:
{context['decisions'] or 'Not available.'}

PREVIOUSLY REJECTED APPROACHES (do not repeat these):
{context['failed_approaches'] or 'Not available.'}

LATEST HANDOVER (what was in progress):
{context['handover'] or 'Not available.'}

Answer in this exact JSON format — no other text:
{{
  "clean": true/false,
  "issues": ["specific issue 1", "specific issue 2"],
  "summary": "one sentence summary of the concern, or 'No architectural concerns found.'"
}}

Rules:
- Only flag REAL contradictions with the documented architecture. Do not invent issues.
- If architecture context is sparse, lean toward clean=true.
- issues array must be empty if clean=true.
- Each issue must be a concrete, specific statement — not a generic warning."""

    try:
        from askr.clients.claude import call_claude
        raw = call_claude(
            "You are a strict architectural reviewer. Output only valid JSON, nothing else.",
            prompt,
            mode="guard",
            query_preview=f"guard check: {reason}",
        )
        # Strip any markdown fencing if Haiku added it
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(raw)
        result["trigger"] = trigger
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        return result
    except Exception as e:
        return {"clean": True, "reason": f"guard check failed: {e}"}


def check_and_save(developer: str, state_dir: str) -> Optional[dict]:
    """
    Read the pending trigger, run the guard check, save the result.
    Returns the result dict, or None if no trigger was pending.
    """
    try:
        if not os.path.exists(_GUARD_TRIGGER_PATH):
            return None
        with open(_GUARD_TRIGGER_PATH) as f:
            trigger = json.load(f)
        os.remove(_GUARD_TRIGGER_PATH)
    except Exception:
        return None

    result = run_guard_check(trigger, developer, state_dir)

    try:
        os.makedirs(os.path.dirname(_GUARD_RESULT_PATH), exist_ok=True)
        with open(_GUARD_RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result


if __name__ == "__main__":
    from askr.state.config import load_developer, get_state_dir
    result = check_and_save(load_developer(), get_state_dir())
    if result:
        print(json.dumps(result, indent=2))
