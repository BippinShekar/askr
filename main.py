import re
from config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM
from modes import MODES
from classifier import classify
from context_loader import load_fast_context, load_snapshot
from client_claude import call_claude
from client_openai import call_openai
from utils import compress

MODE_PREFIXES = list(MODES.keys())

def parse_prefix(query):
    match = re.match(r'^(' + '|'.join(MODE_PREFIXES) + r'):\s*', query, re.IGNORECASE)
    if match:
        return query[match.end():], match.group(1).lower()
    return query, None

def run(query, mode=None, llm=None):
    query, prefix_mode = parse_prefix(query)
    if not mode:
        mode = prefix_mode
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

    system = f"{BASE_SYSTEM_PROMPT}\n{MODES.get(mode, MODES[DEFAULT_MODE])}"

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
