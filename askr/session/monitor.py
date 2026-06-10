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


def stats_path_for_project(project_path: str) -> str:
    """Per-project stats file — isolates concurrent sessions from overwriting each other."""
    hash_ = project_path.replace("/", "-").lstrip("-")
    return os.path.join(_STATS_DIR, hash_ + ".json")


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
