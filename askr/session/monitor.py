#!/usr/bin/env python3
"""
JSONL Session Monitor

Reads the active Claude Code session JSONL to extract context usage.
Quota is tracked separately via usage_api.py (real Anthropic OAuth endpoint).
"""

import os
import json
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional


CLAUDE_PROJECTS_DIR = os.path.expanduser("~/.claude/projects")
_STATS_DIR           = os.path.expanduser("~/.config/askr/stats")


def find_project_root(start_dir: str = None) -> str:
    """Walk up from start_dir to find the project root (.claude or .askr_history present)."""
    d = start_dir or os.getcwd()
    while True:
        if os.path.exists(os.path.join(d, ".claude")) or os.path.exists(os.path.join(d, ".askr_history")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return start_dir or os.getcwd()
        d = parent


def stats_path_for_project(project_path: str) -> str:
    """
    Deterministic placeholder path for "no session data exists yet" — nothing
    writes to this anymore (see session_start.py); callers only use it to get
    a path that is guaranteed not to exist so they can show an empty/idle state.
    """
    hash_ = project_path.replace("/", "-").lstrip("-")
    return os.path.join(_STATS_DIR, hash_ + ".json")


def stats_path_for_session(project_path: str, session_id: str) -> str:
    """Per-session stats file — two concurrent sessions in the same repo each own their file."""
    hash_ = project_path.replace("/", "-").lstrip("-")
    return os.path.join(_STATS_DIR, f"{hash_}_{session_id}.json")


def find_project_stats_files(project_path: str) -> list[str]:
    """
    Return all per-session stats files that belong to this project. Only
    matches {hash}_{session_id}.json — never the legacy {hash}.json (no
    session suffix). That file used to be reset to 0% on every SessionStart
    and never updated again, so it permanently haunted every consumer of
    this list as a second, phantom 0%-context "session" for the same
    project. Nothing writes it anymore (see session_start.py); this
    exclusion also covers any such file left over from before that fix.
    Uses exact prefix + separator check to avoid matching sibling projects
    (e.g. 'askr' must not match 'askr-v2').
    """
    hash_ = project_path.replace("/", "-").lstrip("-")
    result = []
    try:
        for f in os.listdir(_STATS_DIR):
            if not f.endswith(".json"):
                continue
            if f.startswith(f"{hash_}_"):
                result.append(os.path.join(_STATS_DIR, f))
    except Exception:
        pass
    return result


def get_max_context_for_project(project_path: str) -> float:
    """
    Return the highest context_pct across all active session stats files for
    this project. Used by the daemon kill loop to detect when ANY session is
    close to auto-compact, not just the one that last wrote the shared file.
    """
    import time as _time
    max_ctx = 0.0
    now = _time.time()
    for path in find_project_stats_files(project_path):
        try:
            if now - os.path.getmtime(path) > 600:  # SESSION_STALE_SECS
                continue
            with open(path) as f:
                ctx = json.load(f).get("context_pct", 0.0)
            if ctx > max_ctx:
                max_ctx = ctx
        except Exception:
            continue
    return max_ctx


_MODEL_CONTEXT_WINDOWS = {
    "claude-sonnet-4-6": 200_000,
    "claude-opus-4-8":   200_000,
    "claude-haiku-4-5-20251001": 200_000,
    "claude-opus-4-5":   200_000,
}
_DEFAULT_CONTEXT_WINDOW = 200_000


@dataclass
class SessionStats:
    session_id:     str
    session_path:   str
    context_tokens: int
    output_tokens:  int
    context_window: int
    context_pct:    float   # 0.0 to 1.0
    turns:          int     # assistant API exchanges (includes tool calls)
    user_turns:     int     # human messages sent
    model:          str
    last_updated:   datetime


def _project_hash(project_path: str) -> str:
    return project_path.replace("/", "-")


def _find_active_jsonl(project_path: str) -> Optional[str]:
    sessions_dir = os.path.join(CLAUDE_PROJECTS_DIR, _project_hash(project_path))
    if not os.path.isdir(sessions_dir):
        return None
    jsonl_files = [
        os.path.join(sessions_dir, f)
        for f in os.listdir(sessions_dir)
        if f.endswith(".jsonl")
    ]
    if not jsonl_files:
        return None
    return max(jsonl_files, key=os.path.getmtime)


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _total_context_tokens(usage: dict) -> int:
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
    )


def get_session_stats(project_path: str) -> Optional[SessionStats]:
    jsonl_path = _find_active_jsonl(project_path)
    if not jsonl_path:
        return None

    session_id = os.path.basename(jsonl_path).replace(".jsonl", "")
    entries = []
    with open(jsonl_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                pass

    if not entries:
        return None

    model = "claude-sonnet-4-6"
    tokens_per_turn = []
    output_tokens   = 0
    user_turns      = 0

    for e in entries:
        if e.get("type") == "human":
            user_turns += 1
            continue
        if e.get("type") != "assistant":
            continue
        msg   = e.get("message", {})
        usage = msg.get("usage", {})
        if not usage:
            continue
        m = msg.get("model", "")
        if m:
            model = m
        tokens_per_turn.append(_total_context_tokens(usage))
        output_tokens += usage.get("output_tokens", 0)

    context_tokens = tokens_per_turn[-1] if tokens_per_turn else 0
    context_window = _MODEL_CONTEXT_WINDOWS.get(model, _DEFAULT_CONTEXT_WINDOW)
    context_pct    = context_tokens / context_window if context_window > 0 else 0.0

    return SessionStats(
        session_id=session_id,
        session_path=jsonl_path,
        context_tokens=context_tokens,
        output_tokens=output_tokens,
        context_window=context_window,
        context_pct=context_pct,
        turns=len(tokens_per_turn),
        user_turns=user_turns,
        model=model,
        last_updated=datetime.now(timezone.utc),
    )
