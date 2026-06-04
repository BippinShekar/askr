#!/usr/bin/env python3
"""
Context Forecast Engine

Computes the context window label from current usage.
Quota tracking is handled separately via usage_api.py (real Anthropic OAuth endpoint).
"""

from dataclasses import dataclass
from typing import Optional

from askr.session.monitor import SessionStats

CONTEXT_TRIGGER_PCT = 0.90


@dataclass
class Forecast:
    next_trigger:   Optional[str]  # "context" or None
    context_pct:    float          # current 0.0–1.0
    context_label:  str            # "ok" | "high" | "near limit" | "checkpoint"


def get_forecast(stats: SessionStats) -> Forecast:
    context_pct = stats.context_pct

    if context_pct >= CONTEXT_TRIGGER_PCT:
        context_label = "checkpoint"
        next_trigger  = "context"
    elif context_pct >= 0.85:
        context_label = "near limit"
        next_trigger  = "context"
    elif context_pct >= 0.75:
        context_label = "high"
        next_trigger  = None
    else:
        context_label = "ok"
        next_trigger  = None

    return Forecast(
        next_trigger=next_trigger,
        context_pct=context_pct,
        context_label=context_label,
    )
