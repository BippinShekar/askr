#!/usr/bin/env python3
"""
Phase 2 - Dual Forecast Engine

Computes two independent ETAs from SessionStats:
  - Context forecast: turns until context hits CONTEXT_TRIGGER_PCT
  - Quota forecast: minutes until 5h output quota hits QUOTA_TRIGGER_PCT

Whichever fires first becomes the active trigger.
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

from askr.session.monitor import SessionStats

CONTEXT_TRIGGER_PCT = 0.90
QUOTA_TRIGGER_PCT   = 0.85

# Claude Pro empirical 5h output token window. Override via config quota_limit.
_DEFAULT_QUOTA_LIMIT = 88_000


def _load_quota_limit() -> int:
    try:
        config_path = os.path.expanduser("~/.config/askr/config.json")
        with open(config_path) as f:
            val = json.load(f).get("quota_limit")
        if val:
            return int(val)
    except Exception:
        pass
    return _DEFAULT_QUOTA_LIMIT


@dataclass
class Forecast:
    next_trigger: Optional[str]       # "context", "quota", or None
    context_pct: float                # current 0.0-1.0
    quota_pct: float                  # estimated 0.0-1.0
    context_eta_turns: Optional[int]  # turns until context trigger threshold
    quota_eta_minutes: Optional[float]
    reset_at: Optional[datetime]      # session_start + 5h
    quota_limit: int


def get_forecast(stats: SessionStats) -> Forecast:
    quota_limit = _load_quota_limit()

    # --- Context ---
    context_pct = stats.context_pct
    context_eta_turns = None

    if context_pct < CONTEXT_TRIGGER_PCT and len(stats.tokens_per_turn) >= 2:
        recent = stats.tokens_per_turn[-6:]
        deltas = [
            recent[i] - recent[i - 1]
            for i in range(1, len(recent))
            if recent[i] > recent[i - 1]
        ]
        if deltas:
            avg_delta = sum(deltas) / len(deltas)
            remaining = (CONTEXT_TRIGGER_PCT * stats.context_window) - stats.context_tokens
            if avg_delta > 0 and remaining > 0:
                context_eta_turns = max(1, int(remaining / avg_delta))

    # --- Quota ---
    quota_pct = stats.output_tokens_last_5h / quota_limit if quota_limit > 0 else 0.0
    quota_eta_minutes = None
    reset_at = None

    if stats.session_start:
        reset_at = stats.session_start + timedelta(hours=5)
        now = datetime.now(timezone.utc)
        window_remaining_minutes = (reset_at - now).total_seconds() / 60
        if window_remaining_minutes > 0 and quota_pct < QUOTA_TRIGGER_PCT:
            # time remaining scaled by how far we are from the trigger threshold
            fraction_used = quota_pct / QUOTA_TRIGGER_PCT if quota_pct > 0 else 0.0
            quota_eta_minutes = window_remaining_minutes * (1.0 - fraction_used)

    # --- Determine next trigger ---
    immediate = []
    if context_pct >= CONTEXT_TRIGGER_PCT:
        immediate.append("context")
    if quota_pct >= QUOTA_TRIGGER_PCT:
        immediate.append("quota")

    if immediate:
        next_trigger = immediate[0]
    elif context_eta_turns is not None or quota_eta_minutes is not None:
        # Pick whichever fires soonest. Convert turns to minutes (rough: 2 min/turn).
        ctx_minutes = context_eta_turns * 2 if context_eta_turns is not None else float("inf")
        q_minutes   = quota_eta_minutes if quota_eta_minutes is not None else float("inf")
        next_trigger = "context" if ctx_minutes <= q_minutes else "quota"
    else:
        next_trigger = None

    return Forecast(
        next_trigger=next_trigger,
        context_pct=context_pct,
        quota_pct=quota_pct,
        context_eta_turns=context_eta_turns,
        quota_eta_minutes=quota_eta_minutes,
        reset_at=reset_at,
        quota_limit=quota_limit,
    )
