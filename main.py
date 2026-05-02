import re
import subprocess
from datetime import datetime
from config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM, DAILY_BUDGET_USD
from modes import MODES
from context_loader import load_fast_context, load_snapshot, load_file_contents
from snapshot import snapshot_is_stale, build_snapshot
from git_utils import get_diff_summary
from client_claude import call_claude, call_claude_web, MODEL as CLAUDE_MODEL
from client_openai import call_openai
from logger import check_budget
from display import print_progress
from utils import compress

MODE_PREFIXES = list(MODES.keys())
HISTORY_FILE = ".askr_history"

# Narrow, high-signal phrases that almost always need live web data.
# Deliberately specific — generic words like "current" or "latest" alone
# would hit codebase questions and trigger expensive Sonnet calls.
_WEB_SIGNALS = [
    r"\bpric(e|ing|es)\b",
    r"\bcost per\b",
    r"\bper month\b",
    r"\bhow much.{0,40}cost\b",
    r"\bwhat.{0,10}(cost|charge|fee)\b",
    r"\bsubscription\b",
    r"\blatest version\b",
    r"\bcurrent version\b",
    r"\bchangelog\b",
    r"\brelease notes?\b",
    r"\bapi docs?\b",
    r"\bofficial docs?\b",
    r"\bhow to install\b",
    r"\bnpm install\b",
    r"\bpip install\b",
    r"\bbrew install\b",
    r"\bhttp [45]\d{2}\b",
    r"\b[45]\d{2} error\b",
    r"\bstatus code\b",
    r"\bdeprecated\b",
    r"\bwhat.s new in\b",
    r"\bwhen was .+ released\b",
]

_WEB_PATTERN = re.compile("|".join(_WEB_SIGNALS), re.IGNORECASE)


def _auto_web(query):
    return bool(_WEB_PATTERN.search(query))


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

    # Auto-upgrade to web search if query signals live data need,
    # unless the user already set a non-default mode explicitly.
    if mode == DEFAULT_MODE and prefix_mode is None and _auto_web(query):
        mode = "web"
        print_progress("auto: web search triggered")

    if snapshot_is_stale():
        print_progress("updating snapshot...")
        build_snapshot()

    fast_ctx = load_fast_context()
    snapshot = load_snapshot()
    file_contents = load_file_contents(snapshot)

    file_sections = []
    for f in snapshot:
        path = f.get("file", "")
        header = f"FILE: {path} (score:{f.get('_score', 0):.2f})\nPURPOSE: {f.get('purpose', '')}"
        content = file_contents.get(path, "")
        if content:
            header += f"\n---\n{content}"
        file_sections.append(header)
    file_context = "\n\n".join(file_sections)

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
RUNTIME:
date={datetime.now().strftime("%Y-%m-%d")}, model={CLAUDE_MODEL}, cost=$1.00/1M input tokens $5.00/1M output tokens

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
