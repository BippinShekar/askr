#!/usr/bin/env python3
"""
Model context-window cache — read side is instant/offline (hooks call this),
write side is populated by the daemon's poll loop via a live Models API
lookup (usage_api.fetch_model_context_window), authenticated through Claude
Code's own OAuth session. No hardcoded model->window table to go stale on
every new model release; new/unrecognized models self-heal the next time the
daemon sees them, without a code change.
"""

import json
import os

_CACHE_PATH = os.path.expanduser("~/.config/askr/model_context_windows.json")

# Seed only — makes day-one behavior correct with zero network calls for
# models known at the time this file was written. Not the source of truth:
# ensure_cached() overwrites/adds entries from the live Models API on a
# genuine cache miss, so this seed goes stale gracefully instead of silently
# wrong (unlike monitor.py's old hardcoded dict, which had no correction path).
_SEED = {
    "claude-fable-5":     1_000_000,
    "claude-mythos-5":    1_000_000,
    "claude-opus-4-8":    1_000_000,
    "claude-opus-4-7":    1_000_000,
    "claude-opus-4-6":    1_000_000,
    "claude-sonnet-5":    1_000_000,
    "claude-sonnet-4-6":  1_000_000,
    "claude-haiku-4-5":   200_000,
    "claude-haiku-4-5-20251001": 200_000,
}

DEFAULT_CONTEXT_WINDOW = 200_000  # conservative fallback for a model never cached and unreachable live


def _load_cache() -> dict:
    try:
        with open(_CACHE_PATH) as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return dict(_SEED)


def _save_cache(cache: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        tmp_path = f"{_CACHE_PATH}.tmp.{os.getpid()}"
        with open(tmp_path, "w") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
        os.replace(tmp_path, _CACHE_PATH)
    except Exception:
        pass


def get_context_window(model_id: str) -> int:
    """
    Read-only, offline, instant — safe for hooks and any hot path. Never
    triggers a network call; a model this process hasn't cached yet just
    gets the conservative default until the daemon fills it in.
    """
    cache = _load_cache()
    window = cache.get(model_id)
    return int(window) if window else DEFAULT_CONTEXT_WINDOW


def ensure_cached(model_id: str) -> None:
    """
    Daemon-only. On a genuine cache miss, attempts one live Models API
    lookup and persists the result. Safe to call every poll cycle — cache
    hits return immediately with no network; only a truly new model string
    reaches usage_api.fetch_model_context_window(), which itself fails open
    (returns None) on any error so this never raises or blocks the poll loop.
    """
    cache = _load_cache()
    if model_id in cache:
        return
    from askr.session.usage_api import fetch_model_context_window
    window = fetch_model_context_window(model_id)
    if window:
        cache[model_id] = window
        _save_cache(cache)
