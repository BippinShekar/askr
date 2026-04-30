import os
from anthropic import Anthropic
from config import MAX_TOKENS, TEMPERATURE
from dotenv import load_dotenv

load_dotenv(override=True)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODEL = "claude-haiku-4-5-20251001"


def call_claude(system, user, mode="default", query_preview=""):
    res = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}]
    )
    text = res.content[0].text

    try:
        from logger import log_query
        log_query(MODEL, res.usage.input_tokens, res.usage.output_tokens, mode, query_preview)
    except Exception:
        pass

    return text
