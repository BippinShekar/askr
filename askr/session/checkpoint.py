#!/usr/bin/env python3
"""
Checkpoint Engine

Generates handover documentation, updates state files, and commits+pushes.
Called by stop.py (normal session end) and lifecycle.py (threshold triggers).

Handover is written by Haiku from the actual transcript — not from mechanical
parsing of file names and bash commands. The result is actionable context for
the next session to continue work without manual recovery.
"""

import os
import re
import json
import subprocess
from datetime import datetime, timezone
from typing import Optional

_RESULT_PATH        = os.path.expanduser("~/.config/askr/checkpoint_result.json")
_CURSOR_DIR         = os.path.expanduser("~/.config/askr/cursors")
_MAX_TRANSCRIPT_ENTRIES = 60  # enough to capture a substantial work session


def _cursor_path(session_id: str) -> str:
    return os.path.join(_CURSOR_DIR, f"edit_cursor_{session_id}.json")


# ---------------------------------------------------------------------------
# Transcript reading
# ---------------------------------------------------------------------------

def read_transcript(transcript_path: str) -> list:
    if not transcript_path or not os.path.exists(transcript_path):
        return []
    entries = []
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    return entries[-_MAX_TRANSCRIPT_ENTRIES:]


def _extract_tool_actions(entries: list) -> list[str]:
    actions = []
    for entry in entries:
        msg = entry.get("message", {})
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            inp  = block.get("input", {})
            if name in ("Write", "Edit", "MultiEdit"):
                path = inp.get("file_path") or inp.get("path", "")
                if path:
                    actions.append(f"Modified {path}")
            elif name == "Bash":
                cmd = inp.get("command", "")[:80]
                if cmd:
                    actions.append(f"Ran: {cmd}")
    return actions


_SECRET_PATTERNS = [
    # Discord webhook URLs
    (re.compile(r'https://discord\.com/api/webhooks/\d+/[\w-]+'), '[DISCORD_WEBHOOK]'),
    # Anthropic API keys
    (re.compile(r'sk-ant-[A-Za-z0-9_-]{20,}'), '[ANTHROPIC_KEY]'),
    # OpenAI API keys
    (re.compile(r'sk-proj-[A-Za-z0-9_-]{20,}'), '[OPENAI_KEY]'),
    (re.compile(r'sk-[A-Za-z0-9]{40,}'), '[OPENAI_KEY]'),
    # Generic bearer/auth tokens in URLs or headers
    (re.compile(r'Bearer\s+[A-Za-z0-9_\-\.]{20,}'), 'Bearer [TOKEN]'),
    # Generic long hex/base64 tokens that look like secrets (40+ chars of random)
    (re.compile(r'(?<![a-zA-Z0-9/])[A-Za-z0-9+/]{40,}={0,2}(?![a-zA-Z0-9/])'), '[REDACTED]'),
]


def _scrub_secrets(text: str) -> str:
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _build_transcript_text(entries: list) -> str:
    """
    Flatten the transcript to a readable text format for the LLM.
    Includes user messages and assistant text+tool actions — skips hook payloads.
    """
    lines = []
    for entry in entries:
        msg  = entry.get("message", {})
        role = msg.get("role", "")
        if role not in ("user", "assistant"):
            continue
        content = msg.get("content", [])

        if role == "user":
            if isinstance(content, str) and len(content) > 5:
                lines.append(f"USER: {_scrub_secrets(content[:400])}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text", "").strip()
                        if text and len(text) > 5:
                            lines.append(f"USER: {_scrub_secrets(text[:400])}")

        elif role == "assistant":
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text = block.get("text", "").strip()
                            if text:
                                lines.append(f"ASSISTANT: {_scrub_secrets(text[:300])}")
                        elif block.get("type") == "tool_use":
                            name = block.get("name", "")
                            inp  = block.get("input", {})
                            if name in ("Write", "Edit", "MultiEdit"):
                                path = inp.get("file_path") or inp.get("path", "")
                                lines.append(f"TOOL: {name}({path})")
                            elif name == "Bash":
                                cmd = _scrub_secrets(inp.get("command", "")[:80])
                                lines.append(f"TOOL: Bash({cmd})")
                            else:
                                lines.append(f"TOOL: {name}")
    return "\n".join(lines)


def _load_edit_cursor(session_id: str = "") -> dict:
    """Load file→line tracking for this session. Session-scoped to survive parallel sessions."""
    cursor = {}
    if session_id:
        try:
            p = _cursor_path(session_id)
            if os.path.exists(p):
                with open(p) as f:
                    cursor = json.load(f)
        except Exception:
            pass
    return cursor


def _clear_edit_cursor(session_id: str = ""):
    """Delete this session's cursor file after checkpoint."""
    if session_id:
        try:
            p = _cursor_path(session_id)
            if os.path.exists(p):
                os.remove(p)
        except Exception:
            pass


def _get_uncommitted_files() -> list:
    """Ground-truth list of files with uncommitted changes from git."""
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--porcelain"],
            capture_output=True, text=True, timeout=5,
        )
        paths = [line[3:].strip() for line in result.stdout.splitlines() if len(line) > 3]
        # .claude/ is harness config/scratch (gitignored settings, fork worktrees) —
        # never meaningful pending work, but git collapses it to one untracked
        # entry that would otherwise be copied verbatim into the handover.
        return [p for p in paths if not p.startswith(".claude/")]
    except Exception:
        return []


def _generate_handover_with_llm(
    transcript_text: str,
    trigger_type: str = "stop",
    open_goals: list = None,
    session_id: str = "",
    existing_handover: dict = None,
    project_path: str = "",
) -> Optional[dict]:
    """
    Call Haiku to update the project state document from this session's transcript.

    If existing_handover is provided (the current project state), Haiku merges it
    with what this session did — producing a living project state, not a session diary.
    This makes parallel sessions composable: each session end ADDS to project knowledge.
    """
    if not transcript_text.strip():
        return None
    try:
        from askr.clients.claude import call_claude

        edit_cursor = _load_edit_cursor(session_id)
        uncommitted_files = _get_uncommitted_files()

        edit_cursor_text = "\n".join(
            f"  {fp}: line {info.get('line', '?')} (last edit {info.get('ts', '')})"
            for fp, info in edit_cursor.items()
        ) or "  (none tracked this session)"

        goals_section = ""
        if open_goals:
            goals_list = "\n".join(f"- {g}" for g in open_goals)
            goals_section = f"\nOPEN GOALS (check which were completed):\n{goals_list}\n"

        now_iso = datetime.now(timezone.utc).isoformat()
        uncommitted_json = json.dumps(uncommitted_files)

        existing_state_section = ""
        if existing_handover:
            try:
                existing_json = json.dumps(existing_handover, indent=2)[:4000]
                existing_state_section = f"""
EXISTING PROJECT STATE (accumulated from prior sessions — update this, do not erase it):
{existing_json}

"""
            except Exception:
                pass

        prompt = f"""A Claude Code session just ended. Update the project state document to reflect what this session accomplished.

THIS REPOSITORY'S ROOT PATH: {project_path or "(unknown)"}
{existing_state_section}
SESSION TRANSCRIPT (this session only):
{transcript_text}

TRACKED FILE EDITS — ground truth from PostToolUse hook (exact line numbers, not inferred):
{edit_cursor_text}

UNCOMMITTED FILES — from git status (do not change this field):
{chr(10).join(uncommitted_files) if uncommitted_files else "(none)"}
{goals_section}
Output ONLY valid JSON. No markdown fences, no explanation, no preamble. Schema:

{{
  "task": "one sentence PAST-TENSE summary of what the project accomplished across all recent sessions",
  "discussion_summary": "key context, reasoning, and accumulated understanding — 2-4 sentences synthesising all known sessions",
  "accomplishments": [{{"what": "concrete thing completed", "done": true}}],
  "in_progress": [{{"file": "exact/path.py or null if this is not code work", "what": "what is being done here", "last_line": 0}}],
  "next_actions": [
    {{"order": 1, "action": "specific immediately actionable instruction", "why": "why this is next"}},
    {{"order": 2, "action": "...", "why": "..."}}
  ],
  "decisions": [{{"decision": "a choice that rules something out", "reason": "why"}}],
  "user_rejected_decisions": [{{"what_was_proposed": "...", "user_signal": "exact or paraphrased rejection", "domain": "file or area it affects", "confidence": 0.9}}],
  "failed_approaches": [{{"approach": "what was tried", "reason": "why it failed"}}],
  "files_in_play": ["exact/path.py"],
  "relational_files": [{{"file": "exact/path.py", "relationship": "imports|imported_by|configures|tested_by", "why": "why relevant"}}],
  "uncommitted_files": {uncommitted_json},
  "blockers": ["specific blocker"],
  "completed_goals": [],
  "session_metadata": {{"trigger_type": "{trigger_type}", "timestamp": "{now_iso}"}}
}}

session_metadata must contain ONLY trigger_type and timestamp, exactly as given above —
do not add other keys (no "session_end_reason" or similar invented fields), and do not
write anything elsewhere in the document that contradicts trigger_type as the reason this
session ended.

Rules:
- This is a PROJECT STATE document, not a session diary. It accumulates across sessions.
- This document is about the CODEBASE in THIS repository only — root path given above as
  THIS REPOSITORY'S ROOT PATH. If the transcript also covers topics unrelated to this codebase
  (business strategy, fundraising, an unrelated product, etc.) OR real engineering work in a
  DIFFERENT repository (a sibling project the session also touched — check every "TOOL:" line's
  file path against the root path above; a path that does not start with it belongs to another
  repo even if the work looks legitimate and on-topic), EXCLUDE that content entirely from
  task/discussion_summary/accomplishments/in_progress/next_actions/decisions/failed_approaches —
  do not summarize it, do not soften it, just leave it out. This applies EVEN IF there is no
  "TOOL:" line to check — a purely conversational answer or explanation about another named
  project, product, or codebase (no file edits, just discussion) is just as foreign as one
  backed by tool calls. The absence of tool-call evidence is not evidence the content belongs
  here. If the subject matter names a different product/codebase than the one at the root path
  above, or describes decisions/data fields/architecture that has no corresponding file in THIS
  repository, leave it out. Off-topic or foreign-repo content that gets merged in here never
  gets cleaned up automatically and keeps reappearing in every future session's context,
  including in a completely unrelated codebase.
- MERGE, do not replace: keep relevant items from EXISTING PROJECT STATE; update or remove items this session resolved.
- in_progress: REMOVE items this session completed. KEEP still-relevant items from existing state. ADD new in-progress from this session.
- in_progress.file: only set this to a real source file this session was actively editing. Never set it to
  the handover/state files themselves (handover_*.json, handover_*.md, askr_state/*) — those are the output
  of this process, not work in progress. If the session's work has no associated file (e.g. research,
  planning, non-code work), use null.
- next_actions: REMOVE actions this session completed (check git log). KEEP still-valid ones. ADD new ones.
- decisions: KEEP all existing decisions. APPEND new ones from this session. Never lose prior decisions. CRITICAL: guard blocks from the askr PreToolUse hook ("Guard blocked:", "Write blocked", "awaiting Claude correction") are NOT architectural decisions — they are operational events. Never add guard-inferred or guard-rationalized constraints to the decisions array. Only record decisions the developers explicitly made about product or architecture choices.
- failed_approaches: KEEP all existing. APPEND new ones from this session.
- task: PAST TENSE. Describes the overall project state, not just this session's work.
- in_progress.last_line: USE values from TRACKED FILE EDITS — they are exact. Estimate only for unlisted files.
- uncommitted_files: already set above from git — copy it verbatim, do not change.
- user_rejected_decisions: only where the USER rejected a proposal. Confidence >= 0.7 to include.
- completed_goals: list exact goal strings from OPEN GOALS completed THIS SESSION only. Conservative.
- Empty array [] for sections with nothing to report. Never null."""

        raw = call_claude(
            "You generate precise JSON handover documents for autonomous AI coding agents. Output only valid JSON.",
            prompt,
            mode="checkpoint",
            query_preview="handover generation",
        )

        if not raw:
            return None

        cleaned = raw.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            cleaned = parts[1] if len(parts) > 1 else cleaned
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        return json.loads(cleaned)

    except json.JSONDecodeError as e:
        from askr.utils.logger import log_error
        try:
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        log_error("checkpoint._generate_handover_with_llm", f"unparseable JSON, falling back to mechanical summary: {e}")
        return None
    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._generate_handover_with_llm", str(e))
        return None


def _append_failed_approaches(handover, state_dir: str):
    """Append new failed approaches from handover (dict or legacy str) to the cumulative file."""
    if not handover:
        return
    try:
        if isinstance(handover, dict):
            raw_entries = [
                f"{fa.get('approach', '')} — {fa.get('reason', '')}".strip(" —")
                for fa in handover.get("failed_approaches", [])
                if fa.get("approach")
            ]
        else:
            match = re.search(r'## Failed Approaches\n(.*?)(?=\n## |\Z)', handover, re.DOTALL)
            if not match:
                return
            section = match.group(1).strip()
            if not section or section.lower() in ("none", "none.", "unknown"):
                return
            raw_entries = [
                line.strip().lstrip("- ").strip()
                for line in section.splitlines()
                if line.strip().lstrip("- ").strip() and len(line.strip().lstrip("- ").strip()) >= 10
            ]

        if not raw_entries:
            return

        path = os.path.join(state_dir, "failed_approaches.md")
        existing_text = ""
        if os.path.exists(path):
            with open(path) as f:
                existing_text = f.read()

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        header = "" if existing_text else "# Failed Approaches\n\nCumulative cross-session log. Never overwritten — append only.\n\n"

        new_entries = [
            f"- [{ts}] {entry}"
            for entry in raw_entries
            if len(entry) >= 10 and entry.lower() not in existing_text.lower()
        ]

        if not new_entries:
            return

        with open(path, "a") as f:
            if header:
                f.write(header)
            f.write("\n".join(new_entries) + "\n")
    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._append_failed_approaches", str(e))


def _write_decisions_from_handover(handover, state_dir: str, developer: str):
    """Append new decisions from handover JSON to decisions.jsonl (one JSON object per line)."""
    if not isinstance(handover, dict):
        return
    try:
        decisions = handover.get("decisions", [])
        if not decisions:
            return

        path = os.path.join(state_dir, "decisions.jsonl")
        from askr.state.writer import file_lock

        with file_lock(path):
            existing_text = ""
            if os.path.exists(path):
                with open(path) as f:
                    existing_text = f.read().lower()

            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            _guard_signals = (
                "guard blocked", "write blocked", "awaiting claude correction",
                "must be documented", "requires explicit", "outside backend",
                "outside website", "file ownership rules", "merge conflicts",
            )

            new_entries = []
            for d in decisions:
                text   = d.get("decision", "").strip()
                reason = d.get("reason", "").strip()
                if not text or len(text) < 10:
                    continue
                if text.lower() in existing_text:
                    continue
                # Skip decisions that are guard-rationalized operational events
                text_lower = text.lower()
                if any(sig in text_lower for sig in _guard_signals):
                    continue
                new_entries.append(json.dumps({
                    "at": ts, "dev": developer,
                    "decision": text, "reason": reason,
                    "source": "checkpoint",
                }))

            if new_entries:
                with open(path, "a") as f:
                    f.write("\n".join(new_entries) + "\n")
    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._write_decisions_from_handover", str(e))


def _infer_and_queue_tasks(transcript_text: str, state_dir: str, developer: str):
    """
    Scan transcript for natural task assignments ("lochan should handle X",
    "let's have bippin do Y") and queue them automatically.
    Reads team.json to know valid developer names to assign to.
    No-op if transcript is empty, team.json missing, or Haiku call fails.
    """
    if not transcript_text or len(transcript_text) < 100:
        return
    try:
        team_path = os.path.join(state_dir, "team.json")
        if not os.path.exists(team_path):
            return
        with open(team_path) as f:
            members = json.load(f).get("members", [])
        if len(members) < 2:
            return  # solo — nothing to assign

        from askr.clients.claude import call_claude

        members_str = ", ".join(members)
        prompt = f"""You are reading a Claude Code session transcript. Your job is to find any natural task assignments in the conversation — where the user says someone should handle a task, or assigns work to a teammate by name.

Known team members: {members_str}

Look for patterns like:
- "lochan takes care of X"
- "let's have bippin do Y"
- "assign Z to lochan"
- "lochan should handle the auth flow"
- "I'll do X, lochan does Y"

Transcript (last 4000 chars):
{transcript_text[-4000:]}

Return a JSON array of assignments found. Each entry: {{"dev": "<member name>", "task": "<concise task description under 100 chars>"}}.
Only include developers from the known team members list. If no assignments found, return [].
Be conservative — only extract clear, explicit assignments, not vague mentions."""

        raw = call_claude(
            "You extract task assignments from session transcripts. Reply with valid JSON only.",
            prompt,
            mode="default",
            query_preview="task assignment inference",
        )
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

        assignments = json.loads(raw)
        if not isinstance(assignments, list) or not assignments:
            return

        import uuid as _uuid
        tasks_dir = os.path.join(state_dir, "tasks")
        os.makedirs(tasks_dir, exist_ok=True)

        queued = []
        for a in assignments:
            dev  = a.get("dev", "").strip()
            task = a.get("task", "").strip()
            if not dev or not task or dev not in members:
                continue
            entry = json.dumps({
                "id":   _uuid.uuid4().hex[:8],
                "desc": task[:120],
                "from": developer,
                "at":   datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "auto": True,
            })
            queue_path = os.path.join(tasks_dir, f"queue_{dev}.jsonl")
            from askr.state.writer import file_lock
            with file_lock(queue_path):
                with open(queue_path, "a") as f:
                    f.write(entry + "\n")
            queued.append((dev, task))

        if queued:
            import subprocess as _sp
            _sp.run(["git", "add", tasks_dir], capture_output=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            msg = f"askr: auto-queued {len(queued)} task(s) from session [{developer}] {ts}"
            _sp.run(["git", "commit", "-m", msg], capture_output=True)
            _sp.run(["git", "push", "--quiet"], capture_output=True, timeout=30)

    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._infer_and_queue_tasks", str(e))


def _parse_completed_goals_from_handover(handover, open_goals: list) -> list:
    """Extract completed goals from handover (dict or legacy str) and match against open goals."""
    if not handover or not open_goals:
        return []
    try:
        if isinstance(handover, dict):
            completed_strings = handover.get("completed_goals", [])
            if not completed_strings:
                return []
            return [
                g for g in open_goals
                if any(g.lower() in s.lower() or s.lower() in g.lower() for s in completed_strings)
            ]
        else:
            match = re.search(r'## Completed Goals\n(.*?)(?=\n## |\Z)', handover, re.DOTALL)
            if not match:
                return []
            section = match.group(1).strip()
            if section.lower() in ("none", "none.", ""):
                return []
            return [
                g for g in open_goals
                if any(
                    g.lower() in line.lower() or line.lower() in g.lower()
                    for line in section.splitlines()
                    if line.strip().lstrip("- ")
                )
            ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Fallback: mechanical summary when LLM is unavailable
# ---------------------------------------------------------------------------

def _build_fallback_summary(entries: list) -> tuple[str, list]:
    """
    Mechanical fallback when LLM is unavailable.
    Still avoids useless boilerplate — only writes what is actually known.
    """
    tool_actions = _extract_tool_actions(entries)
    user_prompts = []

    for entry in entries:
        msg = entry.get("message", {})
        if msg.get("role") != "user":
            continue
        content = msg.get("content", [])
        if isinstance(content, str) and len(content) > 5:
            user_prompts.append(content[:300])
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "").strip()
                    if text and len(text) > 5:
                        user_prompts.append(text[:300])

    files_changed = sorted(set(
        a.replace("Modified ", "") for a in tool_actions if a.startswith("Modified")
    ))

    sections = []

    task = user_prompts[-1] if user_prompts else "Unknown — transcript unavailable"
    sections.append(f"## Task\n\n{task}")

    if files_changed:
        status_lines = "\n".join(f"- {f} — modified this session, verify state" for f in files_changed[:20])
        sections.append(f"## Status\n\n{status_lines}")
    else:
        sections.append("## Status\n\nUnknown — no file modifications found in transcript")

    sections.append("## Failed Approaches\n\nUnknown — LLM handover unavailable, review transcript manually")

    if files_changed:
        sections.append(f"## Next Action\n\nInspect {files_changed[-1]} — last file modified this session")
    else:
        sections.append("## Next Action\n\nUnknown — run `git diff HEAD~1` to see what changed last session")

    sections.append("## Open Questions\n\nUnknown")

    return "\n\n".join(sections), tool_actions


def _tail_decisions_jsonl(state_dir: str, n: int = 5) -> list:
    """Ground truth recent decisions — this file is append-only and never gutted,
    unlike handover.json's decisions array which can be wiped by a prior degraded run."""
    path = os.path.join(state_dir, "decisions.jsonl")
    try:
        with open(path) as f:
            lines = [l.strip() for l in f if l.strip()]
    except Exception:
        return []
    out = []
    for line in lines[-n:]:
        try:
            d = json.loads(line)
            out.append({"decision": d.get("decision", ""), "reason": d.get("reason", "")})
        except Exception:
            pass
    return out


def _tail_failed_approaches(state_dir: str, n: int = 5) -> list:
    """Ground truth recent failed approaches from the cumulative append-only log."""
    path = os.path.join(state_dir, "failed_approaches.md")
    try:
        with open(path) as f:
            bullets = [l.strip("- ").strip() for l in f if l.strip().startswith("-")]
    except Exception:
        return []
    return [{"approach": b, "reason": ""} for b in bullets[-n:]]


def _build_fallback_handover_dict(entries: list, existing_handover: dict, trigger_type: str, state_dir: str = "") -> dict:
    """
    Degraded handover when the LLM call fails or truncates — used instead of the
    legacy string fallback so write_handover() still updates handover_<dev>.json.

    The string fallback left the JSON untouched, so a stale next_actions list from
    whatever the last successful LLM call wrote (potentially many sessions ago)
    kept surfacing in _infer_direction's git-history walk — feeding completely
    unrelated, ancient directions into later sessions' relaunch prompts.

    decisions/failed_approaches are re-derived from their append-only ground-truth
    files rather than copied from existing_handover — once that dict gets gutted by
    one failed run, copying it forward would keep it empty on every subsequent
    failure too, even though the ground-truth files still have the real history.
    """
    md_summary, tool_actions = _build_fallback_summary(entries)
    files_changed = sorted(set(
        a.replace("Modified ", "") for a in tool_actions if a.startswith("Modified")
    ))
    uncommitted_files = _get_uncommitted_files()

    task = ""
    if "## Task\n\n" in md_summary:
        task = md_summary.split("## Task\n\n", 1)[1].split("\n\n##", 1)[0].strip()

    next_action = (
        f"Inspect {files_changed[-1]} — last file modified this session "
        "(handover generation failed/truncated — verify manually)"
        if files_changed else
        "Handover generation failed/truncated this session — review transcript manually before continuing"
    )

    base = dict(existing_handover) if isinstance(existing_handover, dict) else {}
    base["task"] = task or base.get("task", "")
    base["next_actions"] = [{"order": 1, "action": next_action, "why": "handover generation failed this session"}]
    base["uncommitted_files"] = uncommitted_files
    base.setdefault("in_progress", [])
    base.setdefault("accomplishments", [])
    base["decisions"] = _tail_decisions_jsonl(state_dir) if state_dir else base.get("decisions", [])
    base.setdefault("user_rejected_decisions", [])
    base["failed_approaches"] = _tail_failed_approaches(state_dir) if state_dir else base.get("failed_approaches", [])
    base["files_in_play"] = sorted(set(files_changed) | set(base.get("files_in_play") or []))
    base.setdefault("relational_files", [])
    base.setdefault("blockers", [])
    base.setdefault("completed_goals", [])
    base["session_metadata"] = {
        "trigger_type": trigger_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "degraded": True,
    }
    return base


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

_PUSH_ERROR_LOG = os.path.expanduser("~/.config/askr/checkpoint_error.log")


def _log_push_failure(developer: str, detail: str):
    try:
        os.makedirs(os.path.dirname(_PUSH_ERROR_LOG), exist_ok=True)
        with open(_PUSH_ERROR_LOG, "a") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat()} push failed [{developer}]: {detail.strip()[:500]}\n")
    except Exception:
        pass


def git_commit_push(state_dir: str, developer: str, trigger_type: str):
    cwd = os.path.dirname(os.path.normpath(state_dir))
    try:
        subprocess.run(["git", "add", state_dir], capture_output=True, cwd=cwd)
        result = subprocess.run(
            ["git", "status", "--porcelain", state_dir],
            capture_output=True, text=True, cwd=cwd,
        )
        if not result.stdout.strip():
            return
        ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
        label = "checkpoint" if trigger_type in ("context", "quota", "manual") else trigger_type
        subprocess.run(
            ["git", "commit", "-m", f"askr: {label} [{developer}] {ts}"],
            capture_output=True, cwd=cwd,
        )

        # Concurrent sessions (multi-dev) can push between our commit and our push.
        # Rebase onto the remote first so a non-fast-forward push doesn't get silently
        # dropped — retry once after pulling before giving up.
        last_err = ""
        for attempt in range(2):
            pull = subprocess.run(
                ["git", "pull", "--rebase", "--autostash", "--quiet"],
                capture_output=True, text=True, timeout=30, cwd=cwd,
            )
            if pull.returncode != 0:
                # Rebase conflict or other failure — abort to avoid leaving the repo
                # mid-rebase. Our local commit is preserved; next checkpoint retries.
                subprocess.run(["git", "rebase", "--abort"], capture_output=True, timeout=10, cwd=cwd)
                last_err = pull.stderr or pull.stdout
                break

            push = subprocess.run(
                ["git", "push", "--quiet"], capture_output=True, text=True, timeout=30, cwd=cwd,
            )
            if push.returncode == 0:
                return
            last_err = push.stderr or push.stdout

        _log_push_failure(developer, last_err or "unknown error")
    except Exception as e:
        _log_push_failure(developer, str(e))


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def _run_light_handover(
    trigger_type: str,
    developer: str,
    transcript_path: str = "",
    state_dir: Optional[str] = None,
    session_id: str = "",
):
    """
    Shared core for both create_handover_only() and create_checkpoint(): generate
    and write the handover, then extract decisions/failed_approaches/completed
    goals from that same LLM response. No git commit/push, no Discord/voice, no
    project-brief or architecture regen here — callers layer those on top.

    Returns (result_dict, summary_dict, transcript_text) — the latter two let
    create_checkpoint() reuse this call's output for architecture regen and task
    inference instead of re-running the handover LLM call a second time.
    """
    from askr.state.config import get_state_dir as _get_state_dir
    if state_dir is None:
        state_dir = _get_state_dir()
    # state_dir is always <project_root>/askr_state by convention (config.py,
    # lifecycle.py) — derive the project root from it so git/LLM context below
    # is read from the right repo, not the calling process's ambient cwd.
    project_path = os.path.dirname(os.path.normpath(state_dir))

    entries = read_transcript(transcript_path)

    # Try LLM-generated handover first; fall back to mechanical if unavailable.
    # Emergency (PreCompact) checkpoints go through this same path — the LLM call
    # uses the fast/cheap Haiku "checkpoint" mode already sized for this, and a
    # hardcoded boilerplate summary here previously left handover_<dev>.json stale
    # (write_handover only updates the JSON for dict summaries) and skipped
    # decisions/failed-approaches/task extraction entirely.
    transcript_text = _build_transcript_text(entries)

    # Append git diff so Haiku sees what actually changed, not just which files
    # were touched. This grounds Status and Next Action in reality — especially
    # important when the transcript is thin (autonomous sessions with few text turns).
    try:
        diff_result = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True, text=True, timeout=10, cwd=project_path,
        )
        git_diff = diff_result.stdout.strip()
        if git_diff:
            transcript_text += f"\n\nGIT DIFF (actual changes this session, not yet committed):\n{git_diff[:5000]}"
    except Exception:
        pass

    # Inject recent git log so the LLM never lists already-committed work in next_actions.
    try:
        log_result = subprocess.run(
            ["git", "log", "--oneline", "-15"],
            capture_output=True, text=True, timeout=10, cwd=project_path,
        )
        git_log = log_result.stdout.strip()
        if git_log:
            transcript_text += f"\n\nRECENT GIT LOG (commits already done — do NOT list these in next_actions):\n{git_log}"
    except Exception:
        pass

    # Load open goals so the handover can identify which were completed this session
    open_goals = []
    try:
        from askr.state.goals import load_today_goals, load_open_goals
        open_goals = load_today_goals(state_dir) or load_open_goals(state_dir) or []
    except Exception:
        pass

    # Load existing handover as project state baseline — Haiku will UPDATE it,
    # not replace it. This is what makes parallel sessions composable.
    existing_handover = None
    try:
        from askr.state.reader import load_own_handover_raw
        raw = load_own_handover_raw(developer)
        if isinstance(raw, dict) and raw:
            existing_handover = raw
    except Exception:
        pass

    llm_summary = _generate_handover_with_llm(
        transcript_text,
        trigger_type=trigger_type,
        open_goals=open_goals,
        session_id=session_id,
        existing_handover=existing_handover,
        project_path=project_path,
    )
    if llm_summary:
        summary = llm_summary
    else:
        summary = _build_fallback_handover_dict(entries, existing_handover, trigger_type, state_dir=state_dir)

    from askr.state.writer import write_handover
    handover_path = write_handover(summary, developer, state_dir=state_dir)

    _append_failed_approaches(summary, state_dir)
    _write_decisions_from_handover(summary, state_dir, developer)

    completed_goals = []
    try:
        from askr.state.goals import complete_goal, expire_auto_suggested_goals
        completed_goals = _parse_completed_goals_from_handover(summary, open_goals)
        for g in completed_goals:
            complete_goal(g, state_dir)
        expire_auto_suggested_goals(state_dir)
    except Exception as e:
        # Goal completion depends on the LLM handover succeeding (summary must be
        # the dict form with a completed_goals key — the mechanical fallback summary
        # is a plain string and never closes goals). Log instead of swallowing
        # silently so a real complete_goal() failure isn't invisible.
        from askr.utils.logger import log_error
        log_error("checkpoint.complete_goal", str(e))

    _clear_edit_cursor(session_id)

    result = {
        "trigger": trigger_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "handover_path": handover_path or "",
        "developer": developer,
        "completed_goals": completed_goals,
        "project_path": project_path,
        "state_dir": state_dir,
    }
    return result, summary, transcript_text


def create_handover_only(
    trigger_type: str,
    developer: str,
    transcript_path: str = "",
    state_dir: Optional[str] = None,
    session_id: str = "",
) -> dict:
    """
    Light, every-turn path — this is what askr/hooks/stop.py runs on every single
    Stop hook (i.e. after every assistant reply, not just at session end).

    Generates/updates the handover and extracts decisions, failed approaches, and
    completed goals from that same response. Deliberately does NOT commit/push,
    notify Discord, speak, regenerate project_brief.md, or regenerate
    architecture.md — those cost real LLM calls, git operations, and wall-clock
    time that a routine turn shouldn't have to pay for. Reserved for
    create_checkpoint(), which only runs on the two real emergency conditions
    (quota/context >=90%, or genuine user inactivity).

    Serializes on a per-project checkpoint.lock — the Stop hook fires this on
    every turn, so a burst of rapid replies would otherwise spawn overlapping
    background processes that duplicate the same LLM call and race writing
    handover_bippin.json/.md. A second call within the lock's 45s timeout
    waits for the first to finish rather than running in parallel.
    """
    from askr.state.config import get_state_dir as _get_state_dir
    resolved_state_dir = state_dir or _get_state_dir()
    from askr.state.writer import file_lock
    with file_lock(os.path.join(resolved_state_dir, "checkpoint"), timeout=45):
        result, _, _ = _run_light_handover(trigger_type, developer, transcript_path, resolved_state_dir, session_id)

    try:
        os.makedirs(os.path.dirname(_RESULT_PATH), exist_ok=True)
        with open(_RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    return result


def create_checkpoint(
    trigger_type: str,
    developer: str,
    transcript_path: str = "",
    state_dir: Optional[str] = None,
    session_id: str = "",
) -> dict:
    """
    Heavy/emergency checkpoint: everything create_handover_only() does, plus
    architecture regen, task inference, git commit+push, and a Discord broadcast.

    Only ever called for the two real trigger conditions — quota/context hitting
    the 90% threshold, or genuine user inactivity — never per-turn. project_brief.md
    regen is NOT included here; it's on-demand only (see cli/askr.py `brief` command),
    since nothing in askr's own automation reads it — only a human does.

    trigger_type: "context", "quota", "idle", "manual", "emergency"

    Holds the same per-project checkpoint.lock as create_handover_only() for
    its entire duration (including architecture regen and git commit/push) —
    this is the rare, heavy path, but it still must not race a concurrent
    per-turn handover write for the same project.
    """
    from askr.state.config import get_state_dir as _get_state_dir
    resolved_state_dir = state_dir or _get_state_dir()
    from askr.state.writer import file_lock
    with file_lock(os.path.join(resolved_state_dir, "checkpoint"), timeout=45):
        result, summary, transcript_text = _run_light_handover(
            trigger_type, developer, transcript_path, resolved_state_dir, session_id
        )
        state_dir    = result["state_dir"]
        project_path = result["project_path"]

        _regenerate_architecture_md(project_path, state_dir)
        _infer_and_queue_tasks(transcript_text, state_dir, developer)

        session_duration = 0
        try:
            from askr.state.analytics import record_session_end
            session_duration = record_session_end(trigger_type, developer)
        except Exception:
            pass
        result["duration_seconds"] = session_duration

        git_commit_push(state_dir, developer, trigger_type)

    try:
        os.makedirs(os.path.dirname(_RESULT_PATH), exist_ok=True)
        with open(_RESULT_PATH, "w") as f:
            json.dump(result, f, indent=2)
    except Exception:
        pass

    # Goals are embedded in the checkpoint/stop card — no separate notification needed.
    _notify_discord_checkpoint(trigger_type, developer, result)

    return result


def _regenerate_architecture_md(project_path: str, state_dir: str):
    """
    Regenerate architecture.md from actual import/dependency analysis.
    Runs at each checkpoint so architecture stays current with code changes.
    Skips silently on any failure — never blocks the checkpoint.
    """
    try:
        # Collect Python entry points (routes, main files, controllers)
        py_result = subprocess.run(
            ["find", ".", "-name", "*.py",
             "-not", "-path", "*/venv/*", "-not", "-path", "*/__pycache__/*",
             "-not", "-path", "*/node_modules/*", "-not", "-path", "*/.git/*"],
            capture_output=True, text=True, timeout=10, cwd=project_path,
        )
        py_files = [f.strip() for f in py_result.stdout.splitlines() if f.strip()]

        ts_result = subprocess.run(
            ["find", ".", "(", "-name", "*.ts", "-o", "-name", "*.tsx", ")",
             "-not", "-path", "*/node_modules/*", "-not", "-path", "*/.git/*",
             "-not", "-path", "*/.next/*"],
            capture_output=True, text=True, timeout=10, cwd=project_path,
        )
        ts_files = [f.strip() for f in ts_result.stdout.splitlines() if f.strip()]

        if not py_files and not ts_files:
            return

        # Identify entry points by path pattern
        entry_patterns = ("route", "controller", "main", "app", "index", "server", "api")
        py_entries = [f for f in py_files if any(p in f.lower() for p in entry_patterns)][:15]
        ts_entries = [f for f in ts_files if any(p in f.lower() for p in entry_patterns)][:15]

        # Sample imports from entry points to show dependencies
        def get_imports(filepath, cwd):
            try:
                result = subprocess.run(
                    ["grep", "-h", "-E", r"^(from|import|require|import .* from)", filepath],
                    capture_output=True, text=True, timeout=3, cwd=cwd,
                )
                lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
                return lines[:8]
            except Exception:
                return []

        structure_lines = []
        if py_entries:
            structure_lines.append("Python entry points:")
            for f in py_entries[:8]:
                imps = get_imports(f, project_path)
                structure_lines.append(f"  {f}")
                for imp in imps[:4]:
                    structure_lines.append(f"    {imp}")

        if ts_entries:
            structure_lines.append("TypeScript/Next.js entry points:")
            for f in ts_entries[:8]:
                imps = get_imports(f, project_path)
                structure_lines.append(f"  {f}")
                for imp in imps[:4]:
                    structure_lines.append(f"    {imp}")

        # Summarise directory structure
        dir_result = subprocess.run(
            ["find", ".", "-maxdepth", "2", "-type", "d",
             "-not", "-path", "*/venv/*", "-not", "-path", "*/__pycache__/*",
             "-not", "-path", "*/node_modules/*", "-not", "-path", "*/.git/*",
             "-not", "-path", "*/.next/*"],
            capture_output=True, text=True, timeout=5, cwd=project_path,
        )
        dirs = sorted(set(
            "/".join(d.strip().split("/")[:3])
            for d in dir_result.stdout.splitlines()
            if d.strip() and d.strip() != "."
        ))[:30]

        structure_text = "\n".join(structure_lines)
        dirs_text = "\n".join(dirs)

        prompt = f"""Analyze this codebase structure and write a concise architecture.md that an AI coding agent can use to understand the system before making changes.

DIRECTORY STRUCTURE (top 2 levels):
{dirs_text}

ENTRY POINTS AND THEIR IMPORTS:
{structure_text}

Write architecture.md covering:
1. What the system does (one sentence)
2. Entry points — what triggers execution
3. Core services/modules and their responsibilities
4. Data stores and external integrations
5. Key relationships — which components call which
6. Files that are shared interfaces (changing them affects multiple consumers)

Be specific with file paths. Keep it under 400 words. No generic filler."""

        from askr.clients.claude import call_claude
        result = call_claude(
            "You write concise technical architecture documents from code analysis. Be specific, no filler.",
            prompt,
            mode="checkpoint",
            query_preview="architecture regeneration",
        )
        if result and len(result) > 100:
            arch_path = os.path.join(state_dir, "architecture.md")
            with open(arch_path, "w") as f:
                f.write(f"# Architecture\n\n*Auto-generated at checkpoint — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n\n{result}\n")
    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._regenerate_architecture_md", str(e))


def _generate_project_brief(state_dir: str, developer: str):
    """
    Regenerate project_brief.md from decisions, architecture, goals, and handover.
    Written for a human — co-founder or new hire should be fully oriented from this file alone.
    """
    try:
        decisions_path = os.path.join(state_dir, "decisions.jsonl")
        arch_path      = os.path.join(state_dir, "architecture.md")
        brief_path     = os.path.join(state_dir, "project_brief.md")

        def _read(p):
            try:
                with open(p) as f:
                    return f.read()[:3000]
            except Exception:
                return ""

        def _read_decisions_jsonl(p):
            try:
                lines = []
                with open(p) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        d = json.loads(line)
                        text = f"[{d.get('at','')}] [{d.get('dev','')}] {d.get('decision','')}"
                        if d.get("reason"):
                            text += f". Reason: {d['reason']}"
                        lines.append(text)
                return "\n".join(lines[-30:])
            except Exception:
                return ""

        decisions  = _read_decisions_jsonl(decisions_path)
        arch       = _read(arch_path)

        # Try JSON handover first, then .md fallback
        handover = ""
        json_handover_path = os.path.join(state_dir, f"handover_{developer}.json")
        md_handover_path   = os.path.join(state_dir, f"handover_{developer}.md")
        if os.path.exists(json_handover_path):
            handover = _read(json_handover_path)
        elif os.path.exists(md_handover_path):
            handover = _read(md_handover_path)

        from askr.state.goals import load_open_goals
        open_goals = "\n".join(f"- {g}" for g in (load_open_goals(state_dir) or []))

        if not any([decisions, arch, handover]):
            return

        from askr.clients.claude import call_claude
        prompt = f"""You are writing project_brief.md — a single file that orients any person (co-founder, new hire, returning developer) in under 2 minutes. It answers: what is this product right now, what's actively in flight, what key decisions have been made, and what should someone pick up next.

ARCHITECTURE:
{arch or "Not available."}

RECENT DECISIONS:
{decisions or "Not available."}

OPEN GOALS:
{open_goals or "None."}

LATEST HANDOVER:
{handover or "Not available."}

Write project_brief.md in this format. Plain text only — no emojis, no markdown decorations beyond headers and bullets.

# Project Brief
[One paragraph: what this product is and what problem it solves.]

## What's In Flight
[Bullet list: active work streams, what's being built right now, current milestone.]

## Key Decisions Made
[Bullet list: architectural and product decisions that are settled. Enough context that someone new knows why, not just what.]

## Open Goals
[Bullet list: what's next, in priority order.]

## How to Get Started
[3-4 concrete steps a new developer would take to get oriented and productive. Specific commands where applicable.]

Keep it tight. A person should be able to read this in 90 seconds."""

        brief = call_claude(
            "You write clear, tight technical briefings for software projects. Output only the document.",
            prompt,
            mode="brief",
            query_preview="project brief generation",
        )

        with open(brief_path, "w") as f:
            f.write(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{brief}")

    except Exception as e:
        from askr.utils.logger import log_error
        log_error("checkpoint._generate_project_brief", str(e))


def _notify_discord_goals_completed(goals: list):
    if not goals:
        return
    try:
        from askr.clients.discord import send_message
        lines = "\n".join(f"✓ {g}" for g in goals)
        send_message(f"**[askr] Goal{'s' if len(goals) > 1 else ''} completed**\n{lines}")
    except Exception:
        pass


def _context_history_for_session(project_path: str) -> list[float]:
    """Read per-turn context % from the active JSONL."""
    try:
        from askr.session.monitor import _find_active_jsonl, _total_context_tokens, _MODEL_CONTEXT_WINDOWS, _DEFAULT_CONTEXT_WINDOW
        jsonl_path = _find_active_jsonl(project_path)
        if not jsonl_path:
            return []
        history = []
        model = "claude-sonnet-4-6"
        with open(jsonl_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except Exception:
                    continue
                if entry.get("type") != "assistant":
                    continue
                msg = entry.get("message", {})
                m = msg.get("model", "")
                if m:
                    model = m
                usage = msg.get("usage", {})
                if usage:
                    tokens = _total_context_tokens(usage)
                    window = _MODEL_CONTEXT_WINDOWS.get(model, _DEFAULT_CONTEXT_WINDOW)
                    history.append(tokens / window if window > 0 else 0.0)
        return history
    except Exception:
        return []


def _notify_discord_checkpoint(trigger_type: str, developer: str, result: dict):
    # stop trigger gets its own richer broadcast from stop.py
    if trigger_type == "stop":
        return
    try:
        from askr.session.cost import get_session_cost_summary, record_checkpoint_cost
        from askr.session.report_image import session_card
        from askr.clients.discord import send_file, send_message

        from askr.state.config import load_project_path
        project_path = result.get("project_path") or load_project_path()
        cost_summary = get_session_cost_summary(project_path)
        record_checkpoint_cost(trigger_type, developer, cost_summary)

        duration_seconds = result.get("duration_seconds", 0)

        context_history = _context_history_for_session(project_path)

        completed_goals = result.get("completed_goals", [])

        import subprocess as _sp
        files_changed = []
        try:
            res = _sp.run(["git", "diff", "HEAD~1", "--name-only"],
                          capture_output=True, text=True, cwd=project_path, timeout=5)
            files_changed = [f for f in res.stdout.strip().splitlines()
                             if not f.startswith("askr_state/")]
        except Exception:
            pass

        label = {
            "context":   "Context Checkpoint",
            "quota":     "Quota Checkpoint",
            "manual":    "Manual Checkpoint",
            "emergency": "Emergency Checkpoint",
        }.get(trigger_type, trigger_type.replace("_", " ").title())

        img_path = session_card(
            trigger_type=trigger_type,
            developer=developer,
            cost_summary=cost_summary,
            duration_seconds=duration_seconds,
            goals_completed=completed_goals,
            files_changed=files_changed,
            context_history=context_history,
            project_path=project_path,
        )

        ts = result.get("timestamp", "")[:16].replace("T", " ")
        caption = f"**[askr] {label}** — {developer} @ {ts} UTC"
        if completed_goals:
            caption += "\n" + "  ".join(f"✓ {g}" for g in completed_goals[:3])

        if img_path:
            sent = send_file(img_path, caption)
            try:
                os.remove(img_path)
            except Exception:
                pass
            if not sent:
                send_message(caption + "\nState saved to git. Handover ready.")
        else:
            send_message(caption + "\nState saved to git. Handover ready.")
    except Exception:
        try:
            from askr.clients.discord import send_message
            send_message(f"**[askr] Checkpoint** — {developer}\nState saved to git.")
        except Exception:
            pass
