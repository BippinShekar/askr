import os
from openai import OpenAI
from config import MAX_TOKENS, TEMPERATURE
import env

env.load()

MODEL = "gpt-4o-mini"

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            from display import console
            console.print("\n  [bold red]✗ OPENAI_API_KEY not set[/bold red]")
            console.print("  run [bold]ask setup[/bold] to configure your keys\n")
            raise SystemExit(1)
        _client = OpenAI(api_key=api_key)
    return _client


def call_openai(system, user, mode="default", query_preview=""):
    res = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE
    )
    text = res.choices[0].message.content

    try:
        from logger import log_query
        log_query(MODEL, res.usage.prompt_tokens, res.usage.completion_tokens, mode, query_preview)
    except Exception:
        pass

    return text
