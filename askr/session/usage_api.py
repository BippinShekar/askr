#!/usr/bin/env python3
"""
Quota API — reads real-time session utilization from Anthropic's OAuth usage endpoint.

Claude Code calls this same endpoint internally to power the /usage slash command.
Credentials are read from the macOS Keychain (service: "Claude Code-credentials")
or from the plaintext fallback at ~/.claude/.credentials.json.

Returns five_hour and seven_day utilization percentages (0–100) plus exact reset times.
"""

import json
import os
import platform
import subprocess
import urllib.request
import urllib.error
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

_USAGE_URL      = "https://api.anthropic.com/api/oauth/usage"
_MODELS_URL     = "https://api.anthropic.com/v1/models"
_OAUTH_BETA     = "oauth-2025-04-20"
_ANTHROPIC_VER  = "2023-06-01"
_KEYCHAIN_SVC   = "Claude Code-credentials"
_CREDS_FALLBACK = os.path.expanduser("~/.claude/.credentials.json")


@dataclass
class QuotaStatus:
    five_hour_pct:    float     # 0–100
    five_hour_reset:  datetime  # exact UTC reset time
    seven_day_pct:    float     # 0–100
    seven_day_reset:  datetime  # exact UTC reset time


def _read_keychain() -> Optional[str]:
    """Read the raw JSON blob from macOS Keychain."""
    try:
        username = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
        result = subprocess.run(
            ["security", "find-generic-password", "-a", username, "-w", "-s", _KEYCHAIN_SVC],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _read_creds_file() -> Optional[str]:
    """Read credentials from the plaintext fallback file."""
    try:
        with open(_CREDS_FALLBACK) as f:
            return f.read()
    except Exception:
        return None


def _extract_access_token(raw: str) -> Optional[str]:
    try:
        data = json.loads(raw)
        return data.get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        return None


def _get_access_token() -> Optional[str]:
    if platform.system() == "Darwin":
        raw = _read_keychain()
        if raw:
            token = _extract_access_token(raw)
            if token:
                return token
    raw = _read_creds_file()
    if raw:
        return _extract_access_token(raw)
    return None


def get_quota_status() -> Optional[QuotaStatus]:
    """
    Fetch real-time quota utilization from Anthropic's OAuth usage API.
    Returns None if credentials are unavailable, token is expired, or the request fails.
    Never raises — all failures are swallowed so the caller can treat None as "unknown".
    """
    token = _get_access_token()
    if not token:
        return None

    try:
        req = urllib.request.Request(
            _USAGE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "anthropic-beta": _OAUTH_BETA,
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            # Token expired or invalid — not an error worth logging
            return None
        return None
    except Exception:
        return None

    five_hour  = data.get("five_hour") or {}
    seven_day  = data.get("seven_day") or {}

    five_util  = five_hour.get("utilization")
    five_reset = five_hour.get("resets_at")
    seven_util = seven_day.get("utilization")
    seven_reset = seven_day.get("resets_at")

    if five_util is None or five_reset is None:
        return None

    try:
        five_reset_dt  = datetime.fromisoformat(five_reset.replace("Z", "+00:00"))
        seven_reset_dt = (
            datetime.fromisoformat(seven_reset.replace("Z", "+00:00"))
            if seven_reset else five_reset_dt
        )
    except Exception:
        return None

    return QuotaStatus(
        five_hour_pct=float(five_util),
        five_hour_reset=five_reset_dt,
        seven_day_pct=float(seven_util) if seven_util is not None else 0.0,
        seven_day_reset=seven_reset_dt,
    )


def fetch_model_context_window(model_id: str) -> Optional[int]:
    """
    Look up a model's real context window (max_input_tokens) from the Models
    API, authenticated via Claude Code's own OAuth session — same credential
    source as get_quota_status() above, no separate ANTHROPIC_API_KEY needed.

    Never raises — network/auth/unknown-model failures all return None so the
    caller (the daemon's cache-population pass) can fail open. Callers must
    not put this on a hot path; it's a real HTTP call. The daemon calls this
    only on a genuine cache miss (a model string never seen before).
    """
    token = _get_access_token()
    if not token:
        return None

    try:
        req = urllib.request.Request(
            f"{_MODELS_URL}/{model_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-version": _ANTHROPIC_VER,
                "anthropic-beta": _OAUTH_BETA,
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
    except Exception:
        return None

    window = data.get("max_input_tokens")
    try:
        return int(window) if window else None
    except (TypeError, ValueError):
        return None
