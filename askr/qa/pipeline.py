import re
from datetime import datetime

from askr.utils.config import BASE_SYSTEM_PROMPT, DEFAULT_MODE, DEFAULT_LLM, DAILY_BUDGET_USD
from askr.utils.logger import check_budget
from askr.utils.compress import compress
from askr.utils.display import print_progress
from askr.qa.modes import MODES
from askr.qa.context_loader import load_fast_context, load_snapshot, load_file_contents, load_inventory
from askr.qa.snapshot import snapshot_is_stale, build_snapshot
from askr.utils.git_utils import get_diff_summary
from askr.clients.claude import call_claude, call_claude_web
from askr.clients.openai import call_openai

MODE_PREFIXES = list(MODES.keys())
HISTORY_FILE = ".askr_history"

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


def _load_recent_history(n=5) -> str:
    try:
        with open(HISTORY_FILE) as f:
            content = f.read()
        blocks = [b.strip() for b in content.split("---") if b.strip()]
        recent = blocks[-n:] if len(blocks) >= n else blocks
        if not recent:
            return ""
        return "RECENT CONVERSATION:\n" + "\n---\n".join(recent)
    except FileNotFoundError:
        return ""


def _build_prompt(fast_ctx, inventory, snapshot, mode):
    file_sections = []
    file_contents = load_file_contents(snapshot)
    for f in snapshot:
        path = f.get("file", "")
        parts = [
            f"FILE: {path} (score:{f.get('_score', 0):.2f})",
            f"PURPOSE: {f.get('purpose', '')}",
        ]
        components = f.get("key_components", [])
        if components:
            parts.append("IMPLEMENTS: " + ", ".join(components))
        content = file_contents.get(path, "")
        if content:
            parts.append(f"---\n{content}")
        file_sections.append("\n".join(parts))

    git_context = ""
    if mode == "debug":
        diff = get_diff_summary()
        if diff:
            git_context = f"\nRECENT CHANGES:\n{diff}"

    return f"""CONTEXT:
{fast_ctx}

ALL FILES:
{inventory}

TOP FILES:
{chr(10).join(file_sections)}
{git_context}
"""


def run(query, mode=None, llm=None):
    check_budget(DAILY_BUDGET_USD)

    query, prefix_mode = parse_prefix(query)
    mode = mode or prefix_mode or DEFAULT_MODE
    llm = llm or DEFAULT_LLM

    if mode == DEFAULT_MODE and prefix_mode is None and _auto_web(query):
        mode = "web"
        print_progress("auto: web search triggered")

    if snapshot_is_stale():
        print_progress("updating snapshot...")
        build_snapshot()

    fast_ctx = load_fast_context()
    inventory = load_inventory()
    snapshot = load_snapshot()

    system = f"{BASE_SYSTEM_PROMPT}\n{MODES.get(mode, MODES[DEFAULT_MODE])}"
    recent_history = _load_recent_history(n=5)
    history_block = f"\n{recent_history}\n" if recent_history else ""
    prompt = _build_prompt(fast_ctx, inventory, snapshot, mode) + history_block + f"\nQUESTION:\n{query}"

    if mode == "web":
        res = call_claude_web(system, prompt, mode=mode, query_preview=query[:60])
    elif llm == "claude":
        res = call_claude(system, prompt, mode=mode, query_preview=query[:60])
    else:
        res = call_openai(system, prompt, mode=mode, query_preview=query[:60])

    max_lines = 14 if mode == "web" else (5 if mode == "default" else 8)
    result = compress(res, max_lines=max_lines)
    _save_history(query, mode, result)
    return result, mode
