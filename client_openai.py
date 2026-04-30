from openai import OpenAI
from config import MAX_TOKENS, TEMPERATURE
from dotenv import load_dotenv
import os

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_openai(system, user):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE
    )
    return res.choices[0].message.content