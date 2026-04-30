from config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM
from modes import MODES
from classifier import classify
from context_loader import load_fast_context, load_snapshot
from client_claude import call_claude
from client_openai import call_openai
from utils import compress

def run(query, mode=None, llm=None):
    if not mode:
        c = classify(query)
        mode = c["mode"] if c["confidence"] > 0.6 else DEFAULT_MODE

    llm = llm or DEFAULT_LLM

    fast_ctx = load_fast_context()
    snapshot = load_snapshot()

    context = "\n".join([
        f"{f.get('file')}: {f.get('purpose')}"
        for f in snapshot[:5]
    ])

    system = f"{BASE_SYSTEM_PROMPT}\n{MODES.get(mode)}"

    prompt = f"""
CONTEXT:
{fast_ctx}

FILES:
{context}

QUESTION:
{query}
"""

    if llm == "claude":
        res = call_claude(system, prompt)
    else:
        res = call_openai(system, prompt)

    return compress(res)