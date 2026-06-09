#!/usr/bin/env python3
"""
Context Forecast Engine

Computes the context window label from current usage.
Quota tracking is handled separately via usage_api.py (real Anthropic OAuth endpoint).

Trigger threshold: 65%.
Extended thinking sessions can add 40-80K tokens per turn that aren't visible
in the JSONL until the turn completes (PostToolUse fires on tool calls, not mid-turn).
At 65% of 200K = 130K tokens, there's ~70K buffer for in-flight thinking before
Claude's own auto-compact fires at ~100%.
"""

from dataclasses import dataclass
from typing import Optional

from askr.session.monitor import SessionStats

CONTEXT_TRIGGER_PCT = 0.65


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
    elif context_pct >= 0.50:
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
