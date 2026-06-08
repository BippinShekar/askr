"""
Session cost calculation for Phase 3.7 visual reports.

Computes actual token cost for a session and projects what it would have cost
without askr checkpointing (i.e., if the full context had been sent each turn
rather than being reset at checkpoint boundaries).
"""

from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from typing import Optional

# Prices per million tokens (USD) — input / output
_MODEL_RATES: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6":          (3.00, 15.00),
    "claude-opus-4-8":            (15.00, 75.00),
    "claude-opus-4-5":            (15.00, 75.00),
    "claude-haiku-4-5-20251001":  (0.80,  4.00),
    "claude-haiku-4-5":           (0.80,  4.00),
}
_DEFAULT_RATES = (3.00, 15.00)  # fall back to Sonnet pricing

_STATS_PATH = os.path.expanduser("~/.config/askr/session_stats.json")
_COST_HISTORY_PATH = os.path.expanduser("~/.config/askr/cost_history.json")


def _rates(model: str) -> tuple[float, float]:
    for key, rates in _MODEL_RATES.items():
        if key in model:
            return rates
    return _DEFAULT_RATES


def tokens_to_usd(input_tokens: int, output_tokens: int, model: str = "claude-sonnet-4-6") -> float:
    rate_in, rate_out = _rates(model)
    return (input_tokens * rate_in + output_tokens * rate_out) / 1_000_000


def _load_stats() -> dict:
    try:
        if os.path.exists(_STATS_PATH):
            with open(_STATS_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def get_session_cost_summary(project_path: str = "") -> dict:
    """
    Returns cost data for the current/last session.

    Reads token counts from the active JSONL and session_stats.json.
    Returns a dict with:
      - model
      - context_tokens, output_tokens
      - cost_usd: actual session cost
      - projected_usd: what it would have cost without checkpointing (full context each turn)
      - savings_usd: projected - actual
      - context_pct: how full the context window is
      - turns: number of assistant turns
    """
    stats = _load_stats()
    model = stats.get("model", "claude-sonnet-4-6")
    context_tokens = stats.get("context_tokens", 0)
    context_window = stats.get("context_window", 200_000)
    context_pct    = stats.get("context_pct", 0.0)
    turns          = stats.get("turns", 0)

    # Try to get per-turn token breakdown from JSONL for more accurate cost
    output_tokens = 0
    input_tokens_per_turn: list[int] = []
    output_tokens_per_turn: list[int] = []

    try:
        from askr.session.monitor import _find_active_jsonl
        jsonl_path = _find_active_jsonl(project_path) if project_path else None
        if not jsonl_path and project_path:
            pass
        elif jsonl_path:
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
                    usage = entry.get("message", {}).get("usage", {})
                    if not usage:
                        continue
                    inp = (
                        usage.get("input_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                        + usage.get("cache_creation_input_tokens", 0)
                    )
                    out = usage.get("output_tokens", 0)
                    input_tokens_per_turn.append(inp)
                    output_tokens_per_turn.append(out)
    except Exception:
        pass

    if output_tokens_per_turn:
        output_tokens = sum(output_tokens_per_turn)
        # Actual cost = sum of each turn's (input + output)
        actual_cost = sum(
            tokens_to_usd(i, o, model)
            for i, o in zip(input_tokens_per_turn, output_tokens_per_turn)
        )
        # Projected without checkpointing: each turn sends a growing context.
        # If we had not checkpointed, context would compound linearly.
        # Approximation: average turn context × turns × 1.5 growth factor
        avg_in = sum(input_tokens_per_turn) / len(input_tokens_per_turn) if input_tokens_per_turn else context_tokens
        projected_in = int(avg_in * len(input_tokens_per_turn) * 1.5)
        projected_out = output_tokens
        projected_cost = tokens_to_usd(projected_in, projected_out, model)
    else:
        # Fallback: estimate from context tokens
        actual_cost = tokens_to_usd(context_tokens, context_tokens // 4, model)
        projected_cost = actual_cost * 2.0
        output_tokens = context_tokens // 4

    savings = max(0.0, projected_cost - actual_cost)

    return {
        "model": model,
        "context_tokens": context_tokens,
        "output_tokens": output_tokens,
        "context_window": context_window,
        "context_pct": context_pct,
        "turns": turns,
        "cost_usd": round(actual_cost, 4),
        "projected_usd": round(projected_cost, 4),
        "savings_usd": round(savings, 4),
    }


def record_checkpoint_cost(trigger_type: str, developer: str, cost_summary: dict):
    """Append cost record to cost_history.json for morning report aggregation."""
    try:
        entry = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trigger": trigger_type,
            "developer": developer,
            **cost_summary,
        }
        history = []
        if os.path.exists(_COST_HISTORY_PATH):
            with open(_COST_HISTORY_PATH) as f:
                history = json.load(f)
        history.append(entry)
        os.makedirs(os.path.dirname(_COST_HISTORY_PATH), exist_ok=True)
        with open(_COST_HISTORY_PATH, "w") as f:
            json.dump(history[-200:], f, indent=2)  # keep last 200 records
    except Exception:
        pass


def today_cost_summary() -> dict:
    """Aggregate all today's cost records for the morning report."""
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        if not os.path.exists(_COST_HISTORY_PATH):
            return {}
        with open(_COST_HISTORY_PATH) as f:
            history = json.load(f)
        entries = [e for e in history if e.get("date") == today]
        if not entries:
            return {}
        return {
            "sessions": len(entries),
            "total_cost_usd": round(sum(e.get("cost_usd", 0) for e in entries), 4),
            "total_projected_usd": round(sum(e.get("projected_usd", 0) for e in entries), 4),
            "total_savings_usd": round(sum(e.get("savings_usd", 0) for e in entries), 4),
            "total_tokens": sum(e.get("context_tokens", 0) for e in entries),
        }
    except Exception:
        return {}
