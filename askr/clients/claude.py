import os
from anthropic import Anthropic
from askr.utils.config import MAX_TOKENS, TEMPERATURE
from askr.utils import env

env.load()

MODEL = "claude-haiku-4-5-20251001"
WEB_MODEL = "claude-sonnet-4-6"
WEB_MAX_TOKENS = 700

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            from askr.utils.display import console
            console.print("\n  [bold red]✗ ANTHROPIC_API_KEY not set[/bold red]")
            console.print("  run [bold]ask setup[/bold] to configure your keys\n")
            raise SystemExit(1)
        _client = Anthropic(api_key=api_key)
    return _client


_MODE_MAX_TOKENS = {
    "checkpoint": 2000,  # handover + Completed Goals section — 300 truncates mid-sentence
    "guard":       500,  # JSON response: {"clean":..,"issues":[..],"summary":..} — 300 truncates
}


def call_claude(system, user, mode="default", query_preview=""):
    max_tokens = _MODE_MAX_TOKENS.get(mode, MAX_TOKENS)
    res = _get_client().messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=TEMPERATURE,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}]
    )
    text = res.content[0].text

    try:
        from askr.utils.logger import log_query
        log_query(MODEL, res.usage.input_tokens, res.usage.output_tokens, mode, query_preview)
    except Exception:
        pass

    return text


def call_claude_web(system, user, mode="web", query_preview=""):
    res = _get_client().messages.create(
        model=WEB_MODEL,
        max_tokens=WEB_MAX_TOKENS,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}],
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]
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
