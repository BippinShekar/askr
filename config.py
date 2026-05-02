BASE_SYSTEM_PROMPT = """
- No fluff
- No introductions
- No restating question
- Minimal tokens only
"""

MAX_TOKENS = 300
TEMPERATURE = 0.2

DEFAULT_MODE = "default"
FALLBACK_MODE = "quick"
DEFAULT_LLM = "claude"

SNAPSHOT_DIR = ".llm_snapshot"
DAILY_BUDGET_USD = 1.00