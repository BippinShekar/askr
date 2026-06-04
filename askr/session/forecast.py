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
    next_trigger: Optional[str]        # "context", "quota", or None
    context_pct: float                 # current 0.0-1.0
    context_label: str                 # "ok" | "high" | "near limit" | "checkpoint"
    quota_eta_minutes: Optional[float] # minutes until 5h window resets
    reset_at: Optional[datetime]       # session_start + 5h


def get_forecast(stats: SessionStats) -> Forecast:
    quota_limit = _load_quota_limit()

    # --- Context ---
    context_pct = stats.context_pct
    # Turn-based ETA removed: rolling averages are too noisy (a turn reading files
    # vs a turn giving a short answer can differ 10x in token growth). The % and
    # threshold labels are the honest signal; a turn count implies false precision.
    context_eta_turns = None

    # --- Quota ---
    # We do NOT calculate quota_pct from output tokens — Anthropic's formula is
    # internal and any hardcoded limit produces wildly wrong numbers.
    # Trigger B fires purely on time: ≤ 30 min left in the 5h window.
    quota_eta_minutes = None
    reset_at = None

    if stats.session_start:
        reset_at = stats.session_start + timedelta(hours=5)
        now = datetime.now(timezone.utc)
        window_remaining_minutes = (reset_at - now).total_seconds() / 60
        if window_remaining_minutes > 0:
            quota_eta_minutes = window_remaining_minutes

    # --- Determine next trigger ---
    immediate = []
    if context_pct >= CONTEXT_TRIGGER_PCT:
        immediate.append("context")

    if immediate:
        next_trigger = immediate[0]
    elif context_eta_turns is not None or quota_eta_minutes is not None:
        # Pick whichever fires soonest. Convert turns to minutes (rough: 2 min/turn).
        ctx_minutes = context_eta_turns * 2 if context_eta_turns is not None else float("inf")
        q_minutes   = quota_eta_minutes if quota_eta_minutes is not None else float("inf")
        next_trigger = "context" if ctx_minutes <= q_minutes else "quota"
    else:
        next_trigger = None

    if context_pct >= CONTEXT_TRIGGER_PCT:
        context_label = "checkpoint"
    elif context_pct >= 0.85:
        context_label = "near limit"
    elif context_pct >= 0.75:
        context_label = "high"
    else:
        context_label = "ok"

    return Forecast(
        next_trigger=next_trigger,
        context_pct=context_pct,
        context_label=context_label,
        quota_eta_minutes=quota_eta_minutes,
        reset_at=reset_at,
    )
