import os
import json
import urllib.request
import urllib.error

from askr.utils.config import MAX_TOKENS, TEMPERATURE
from askr.utils import env

env.load()

MODEL = "claude-haiku-4-5-20251001"
WEB_MODEL = "claude-sonnet-4-6"
WEB_MAX_TOKENS = 700

_MESSAGES_URL   = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VER  = "2023-06-01"
_OAUTH_BETA     = "oauth-2025-04-20"

_MODE_MAX_TOKENS = {
    "checkpoint": 4000,  # handover + Completed Goals section — was 2000, observed truncating
                         # mid-JSON on real sessions (usage.log: out=2000 exactly, json.loads
                         # failed, fell back to the mechanical/generic handover)
    "guard":       500,  # JSON response: {"clean":..,"issues":[..],"summary":..} — 300 truncates
}


# ---------------------------------------------------------------------------
# OAuth transport — every internal askr LLM call (handover, guard, architecture,
# project brief, goal inference, task-queue inference) goes through this. It
# authenticates via Claude Code's own OAuth session token — the same one
# askr/session/usage_api.py reads from the macOS Keychain to check quota —
# instead of a separate ANTHROPIC_API_KEY. Background checkpointing draws from
# the Claude Code subscription's own usage window, not a second, separately
# metered credit balance.
#
# Deliberately NOT used by askr/qa/pipeline.py (the `ask <query>` command,
# below) — that command exists specifically to keep answering questions about
# the repo after Claude Code's own session/quota is exhausted, so it needs a
# credential independent of that same quota, not this one.
# ---------------------------------------------------------------------------

def _get_oauth_token() -> str:
    from askr.session.usage_api import _get_access_token
    token = _get_access_token()
    if not token:
        from askr.utils.display import console
        console.print("\n  [bold red]✗ couldn't read Claude Code's OAuth token[/bold red]")
        console.print("  make sure you're logged in: run [bold]claude auth[/bold]\n")
        raise SystemExit(1)
    return token


def _post_messages(body: dict, mode: str, query_preview: str) -> dict:
    token = _get_oauth_token()
    req = urllib.request.Request(
        _MESSAGES_URL,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "anthropic-version": _ANTHROPIC_VER,
            "anthropic-beta": _OAUTH_BETA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        from askr.utils.logger import log_error
        log_error(f"claude._post_messages[{mode}]", f"HTTP {e.code}: {detail}")
        raise RuntimeError(f"Claude OAuth call failed (HTTP {e.code}): {detail}")

    try:
        from askr.utils.logger import log_oauth_query
        usage = data.get("usage", {})
        log_oauth_query(body["model"], usage.get("input_tokens", 0), usage.get("output_tokens", 0),
                         mode, query_preview)
    except Exception:
        pass

    return data


def call_claude(system, user, mode="default", query_preview=""):
    max_tokens = _MODE_MAX_TOKENS.get(mode, MAX_TOKENS)
    data = _post_messages({
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": TEMPERATURE,
        "system": system or "You are a helpful assistant.",
        "messages": [{"role": "user", "content": user}],
    }, mode, query_preview)
    return data["content"][0]["text"]


def call_claude_web(system, user, mode="web", query_preview=""):
    data = _post_messages({
        "model": WEB_MODEL,
        "max_tokens": WEB_MAX_TOKENS,
        "system": system or "You are a helpful assistant.",
        "messages": [{"role": "user", "content": user}],
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
    }, mode, query_preview)

    return "\n".join(
        block["text"] for block in data.get("content", [])
        if block.get("type") == "text" and block.get("text")
    ).strip()


# ---------------------------------------------------------------------------
# API-key transport — used ONLY by askr/qa/pipeline.py (the `ask <query>` CLI
# command). That command's whole purpose is to keep answering repo questions
# after Claude Code's own session/quota is exhausted, so it must draw from a
# credential that isn't drained by the same quota the OAuth functions above
# consume — a real, separately-billed ANTHROPIC_API_KEY the user opts into via
# `ask setup`, not Claude Code's own login.
# ---------------------------------------------------------------------------

_api_client = None


def _get_api_client():
    global _api_client
    if _api_client is None:
        from anthropic import Anthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            from askr.utils.display import console
            console.print("\n  [bold red]✗ ANTHROPIC_API_KEY not set[/bold red]")
            console.print("  run [bold]ask setup[/bold] to configure your keys\n")
            raise SystemExit(1)
        _api_client = Anthropic(api_key=api_key)
    return _api_client


def call_claude_api_key(system, user, mode="default", query_preview=""):
    max_tokens = _MODE_MAX_TOKENS.get(mode, MAX_TOKENS)
    res = _get_api_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=TEMPERATURE,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}],
    )
    text = res.content[0].text
    try:
        from askr.utils.logger import log_query
        log_query(MODEL, res.usage.input_tokens, res.usage.output_tokens, mode, query_preview)
    except Exception:
        pass
    return text


def call_claude_web_api_key(system, user, mode="web", query_preview=""):
    res = _get_api_client().messages.create(
        model=WEB_MODEL,
        max_tokens=WEB_MAX_TOKENS,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
    )
    text = "\n".join(
        block.text for block in res.content
        if hasattr(block, "text") and block.text
    ).strip()
    try:
        from askr.utils.logger import log_query
        log_query(WEB_MODEL, res.usage.input_tokens, res.usage.output_tokens, mode, query_preview)
    except Exception:
        pass
    return text
