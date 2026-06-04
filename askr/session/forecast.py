#!/usr/bin/env python3
"""
Context Forecast Engine

Computes the context window label from current usage.
Quota tracking is handled separately via usage_api.py (real Anthropic OAuth endpoint).

Trigger threshold: 75%.
Research basis: Adobe study shows Claude Sonnet degrades from 88%→30% accuracy on
multi-step reasoning at long context. Community consensus is 70-80%. Anthropic's own
docs call 95% (their compaction default) "already too late." 75% gives enough buffer
to write a coherent handover before quality fully collapses.
"""

from dataclasses import dataclass
from typing import Optional

from askr.session.monitor import SessionStats

CONTEXT_TRIGGER_PCT = 0.75


@dataclass
class Forecast:
    next_trigger:   Optional[str]  # "context" or None
    context_pct:    float          # current 0.0–1.0
    context_label:  str            # "ok" | "getting full" | "checkpoint"


def get_forecast(stats: SessionStats) -> Forecast:
    context_pct = stats.context_pct

    if context_pct >= CONTEXT_TRIGGER_PCT:
        context_label = "checkpoint"
        next_trigger  = "context"
    elif context_pct >= 0.60:
        context_label = "getting full"
        next_trigger  = None
    else:
        context_label = "ok"
        next_trigger  = None

    return Forecast(
        next_trigger=next_trigger,
        context_pct=context_pct,
        context_label=context_label,
    )
