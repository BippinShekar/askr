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
import time
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


_GUARD_SIGNAL_PHRASES = (
    "guard blocked", "write blocked", "awaiting claude correction",
    "must be documented", "requires explicit", "outside backend",
    "outside website", "file ownership rules", "merge conflicts",
    "requires approval", "must be approved", "prior to implementation",
    "before implementation", "not documented in architecture",
)


def _load_recent_decisions(state_dir: str, limit_lines: int = 30) -> str:
    path = os.path.join(state_dir, "decisions.jsonl")
    if not os.path.exists(path):
        return ""
    lines = []
    with open(path) as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                d = json.loads(raw_line)
                # Missing source means it was written without explicit tagging — treat
                # as unknown (soft), not user_approved. All authoritative decisions
                # written by checkpoint.py carry source="checkpoint" explicitly.
                source = d.get("source", "unknown")
                decision_text = d.get("decision", "")

                # Skip decisions that smell like guard-rationalized operational events.
                # These are self-reinforcing: guard blocks → Claude or stop hook writes a
                # "constraint" decision → guard reads it → blocks again.
                text_lower = decision_text.lower()
                if any(sig in text_lower for sig in _GUARD_SIGNAL_PHRASES):
                    continue

                text = f"[{d.get('at', '')}] [{d.get('dev', '')}] {decision_text}"
                if d.get("reason"):
                    text += f". Reason: {d['reason']}"
                # All non-user-approved sources are soft context only
                if source != "user_approved":
                    text = f"[soft/inferred] {text}"
                lines.append(text)
            except Exception:
                pass
    return "\n".join(lines[-limit_lines:])


_CODE_KEYWORDS = (
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java",
    "function", "class ", "import ", "export ", "endpoint", "route",
    "component", "controller", "service", "api", "schema", "model",
    "database", "migration", "hook", "middleware", "handler",
)

_ARCH_STALE_HOURS = 2


def _load_failed_approaches(state_dir: str) -> str:
    """Load failed_approaches.md filtered to code-relevant entries only."""
    path = os.path.join(state_dir, "failed_approaches.md")
    if not os.path.exists(path):
        return ""
    lines = []
    try:
        with open(path) as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                lower = stripped.lower()
                if any(kw in lower for kw in _CODE_KEYWORDS):
                    lines.append(stripped)
    except Exception:
        return ""
    return "\n".join(lines[-20:])


def _load_rejected_decisions(state_dir: str, file_path: str = "", limit_lines: int = 20) -> str:
    """Load rejected_decisions.jsonl (Phase 3.13) filtered to entries whose
    domain matches the file being written/edited.

    Simple substring match either direction — not a path resolver. If
    file_path is empty, entries with no domain fall through unfiltered; if
    file_path is given, entries are only included when domain and file_path
    overlap as substrings. Keeping this simple by design (see roadmap.md
    Phase 3.13 S3) — under-matching a broad "domain" description (an area of
    the codebase rather than an exact path) is an accepted limitation.
    """
    path = os.path.join(state_dir, "rejected_decisions.jsonl")
    if not os.path.exists(path):
        return ""
    file_lower = (file_path or "").lower()
    lines = []
    try:
        with open(path) as f:
            for raw_line in f:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    d = json.loads(raw_line)
                except Exception:
                    continue
                domain = d.get("domain", "").strip()
                if file_lower:
                    domain_lower = domain.lower()
                    if not domain_lower or (domain_lower not in file_lower and file_lower not in domain_lower):
                        continue
                text = (
                    f"[{d.get('at', '')}] [{d.get('dev', '')}] "
                    f"Proposed: {d.get('what_was_proposed', '')} — "
                    f"User rejected (\"{d.get('user_signal', '')}\"), domain: {domain or 'unspecified'}"
                )
                lines.append(text)
    except Exception:
        return ""
    return "\n".join(lines[-limit_lines:])


def _load_architecture(state_dir: str) -> str:
    """Load architecture.md and append a staleness warning if it's older than 2 hours."""
    path = os.path.join(state_dir, "architecture.md")
    content = _read(path)
    if not content:
        return ""
    try:
        age_hours = (time.time() - os.path.getmtime(path)) / 3600
        if age_hours > _ARCH_STALE_HOURS:
            content += (
                f"\n\n[NOTE: This architecture snapshot is {age_hours:.0f}h old — "
                f"new directories or files added since then are NOT documented here. "
                f"Absence of a path does NOT mean it is prohibited.]"
            )
    except Exception:
        pass
    return content


def _load_context(developer: str, state_dir: str, file_path: str = "") -> dict:
    return {
        "architecture":       _load_architecture(state_dir),
        "handover":           _read(os.path.join(state_dir, f"handover_{developer}.md")),
        "decisions":          _load_recent_decisions(state_dir),
        "failed_approaches":  _load_failed_approaches(state_dir),
        "rejected_decisions": _load_rejected_decisions(state_dir, file_path),
    }


def run_guard_check(trigger: dict, developer: str, state_dir: str) -> dict:
    """
    Cross-check the triggered change against architecture context.
    Returns {"clean": True} or {"clean": False, "issues": [...], "summary": str}
    """
    reason    = trigger.get("reason", "")
    tool      = trigger.get("tool", "")
    file_path = trigger.get("file_path", "")

    context = _load_context(developer, state_dir, file_path)

    if not any(context.values()):
        return {"clean": True, "reason": "no architecture context available"}

    if reason == "new_file":
        if os.path.exists(file_path):
            # File was new when first blocked but now exists (retry after block)
            reason_label = f"Claude is modifying an existing file (flagged when first created): {file_path}"
        else:
            reason_label = f"Claude is creating a new file: {file_path}"
    elif reason == "batch_writes":
        reason_label = f"Claude has made multiple file edits this session (batch implementation detected). Latest: {file_path}"
    elif reason == "shared_interface":
        reason_label = f"Claude is editing a shared/core interface: {file_path}"
    else:
        reason_label = f"Claude is modifying: {file_path}"

    prompt = f"""An AI coding agent is about to make a significant change to a codebase. Your job is to check whether this change contradicts the known architecture, repeats a previously-rejected approach, or conflicts with settled decisions.

TRIGGER:
{reason_label}

ARCHITECTURE:
{context['architecture'] or 'Not available.'}

SETTLED DECISIONS (decisions marked [soft/inferred] are checkpoint-generated context, not hard constraints — weight them lightly):
{context['decisions'] or 'Not available.'}

PREVIOUSLY REJECTED APPROACHES (technical dead ends — do not repeat these):
{context['failed_approaches'] or 'Not available.'}

USER-REJECTED DECISIONS (Claude proposed these and the user explicitly said no — do not re-propose them):
{context['rejected_decisions'] or 'Not available.'}

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
- CRITICAL: Absence of a file, directory, or pattern in the architecture docs does NOT mean it is prohibited. Only block if architecture or a settled decision EXPLICITLY forbids the approach. "Not mentioned" is NOT a contradiction.
- If architecture context is sparse, lean toward clean=true.
- Do not treat location-based concerns (file is outside backend/ or website/) as a block unless the architecture explicitly states that directory is off-limits.
- Guard-inferred constraints from prior session blocks (e.g. "must be documented first", "requires explicit approval") are soft context only — do not use them as hard blocks.
- If the proposed change matches a USER-REJECTED DECISION, flag it clearly — cite the exact "what_was_proposed" text and the user's rejection signal.
- issues array must be empty if clean=true.
- Each issue must cite the specific line or decision text that is contradicted — not a generic warning."""

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
