import os
from anthropic import Anthropic
from config import MAX_TOKENS, TEMPERATURE
from dotenv import load_dotenv

load_dotenv(override=True)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def call_claude(system, user):
    res = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system or "You are a helpful assistant.",
        messages=[{"role": "user", "content": user}]
    )
    return res.content[0].text
