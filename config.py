BASE_SYSTEM_PROMPT = """
- No fluff
- No introductions
- No restating question
- Minimal tokens only
- Never comment on the clarity, quality, or phrasing of the question — just answer it
- Always pick the most reasonable interpretation and answer directly
- Never say a question is out of scope — the question is always about the current codebase
"""

MAX_TOKENS = 300
TEMPERATURE = 0.2

DEFAULT_MODE = "default"
FALLBACK_MODE = "quick"
DEFAULT_LLM = "claude"

SNAPSHOT_DIR = ".llm_snapshot"
DAILY_BUDGET_USD = 1.00