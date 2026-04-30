import requests
import os
from config import MAX_TOKENS, TEMPERATURE
from dotenv import load_dotenv

load_dotenv(override=True)

def call_claude(system, user):
    res = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": os.getenv("CLAUDE_API_KEY"),
            "anthropic-version": "2023-06-01"
        },
        json={
            "model": "claude-3-5-sonnet",
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        }
    )
    return res.json()["content"][0]["text"]