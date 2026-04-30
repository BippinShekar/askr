import re
import subprocess
from datetime import datetime
from config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM, DAILY_BUDGET_USD
from modes import MODES
from context_loader import load_fast_context, load_snapshot
from snapshot import snapshot_is_stale, build_snapshot
from git_utils import get_diff_summary
from client_claude import call_claude, call_claude_web
from client_openai import call_openai
from logger import check_budget
from display import print_progress
from utils import compress

MODE_PREFIXES = list(MODES.keys())
HISTORY_FILE = ".askr_history"


def parse_prefix(query):
    pattern = r'^(' + '|'.join(MODE_PREFIXES) + r'):\s*'
    match = re.match(pattern, query, re.IGNORECASE)
    if match:
        return query[match.end():], match.group(1).lower()
    return query, None


def _save_history(query, mode, response):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    block = f"[{ts}] [{mode}]\nQ: {query}\nA: {response}\n---\n"
    with open(HISTORY_FILE, "a") as f:
        f.write(block)


def _copy_to_clipboard(text):
    try:
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
    except Exception:
        pass


def run(query, mode=None, llm=None):
    check_budget(DAILY_BUDGET_USD)

    query, prefix_mode = parse_prefix(query)
    mode = mode or prefix_mode or DEFAULT_MODE
    llm = llm or DEFAULT_LLM

    if snapshot_is_stale():
        print_progress("updating snapshot...")
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

    if mode == "web":
        res = call_claude_web(system, prompt, mode=mode, query_preview=query[:60])
    elif llm == "claude":
        res = call_claude(system, prompt, mode=mode, query_preview=query[:60])
    else:
        res = call_openai(system, prompt, mode=mode, query_preview=query[:60])

    max_lines = 14 if mode == "web" else 8
    result = compress(res, max_lines=max_lines)
    _save_history(query, mode, result)
    _copy_to_clipboard(result)
    return result, mode
