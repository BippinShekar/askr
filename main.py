import re
from config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM
from modes import MODES
from classifier import classify
from context_loader import load_fast_context, load_snapshot
from snapshot import snapshot_is_stale, build_snapshot
from git_utils import get_diff_summary
from client_claude import call_claude
from client_openai import call_openai
from utils import compress

MODE_PREFIXES = list(MODES.keys())


def parse_prefix(query):
    pattern = r'^(' + '|'.join(MODE_PREFIXES) + r'):\s*'
    match = re.match(pattern, query, re.IGNORECASE)
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

    if snapshot_is_stale():
        print("(updating snapshot...)")
        build_snapshot()

    fast_ctx = load_fast_context()
    snapshot = load_snapshot()

    file_context = "\n".join([
        f"{f.get('file')} (score:{f.get('_score', 0):.2f}): {f.get('purpose', '')}"
        for f in snapshot
    ])

    git_context = ""
    if mode == "debug":
        diff = get_diff_summary()
        if diff:
            git_context = f"\nRECENT CHANGES:\n{diff}"

    system = f"{BASE_SYSTEM_PROMPT}\n{MODES.get(mode, MODES[DEFAULT_MODE])}"

    prompt = f"""CONTEXT:
{fast_ctx}

FILES:
{file_context}
{git_context}
QUESTION:
{query}
"""

    if llm == "claude":
        res = call_claude(system, prompt)
    else:
        res = call_openai(system, prompt)

    return compress(res)
