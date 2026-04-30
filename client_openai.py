import os
from openai import OpenAI
from config import MAX_TOKENS, TEMPERATURE
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MODEL = "gpt-4o-mini"


def call_openai(system, user, mode="default", query_preview=""):
    res = client.chat.completions.create(
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
