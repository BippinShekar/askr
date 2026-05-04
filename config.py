BASE_SYSTEM_PROMPT = """
- No fluff
- No introductions
- No restating question
- Minimal tokens only
- Never ask for clarification — pick the most reasonable interpretation and answer it
- Never say a question is out of scope — the question is always about the current codebase
- Never offer alternative phrasings or suggest the user rephrase
"""

MAX_TOKENS = 300
TEMPERATURE = 0.2

DEFAULT_MODE = "default"
FALLBACK_MODE = "quick"
DEFAULT_LLM = "claude"

SNAPSHOT_DIR = ".llm_snapshot"
DAILY_BUDGET_USD = 1.00