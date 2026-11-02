import os
from pathlib import Path
from dotenv import load_dotenv

# .env next to the repo root (two levels up from askr/utils/env.py)
_REPO_ENV = Path(__file__).parent.parent.parent / ".env"


# Every Claude call askr makes goes through the user's Claude subscription
# (the Claude Code login), never a separately billed API key. These are never
# loaded from askr's .env files: once in os.environ they're inherited by every
# hook, the daemons, and any `claude` they launch — and Claude Code prefers an
# API key over the subscription login (found 2026-11-02: voice tasks failed
# with "Credit balance is too low" on an empty API account).
_NEVER_LOAD = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


def load():
    """
    Load keys in priority order:
      1. ASKR_ENV env var (set by brew wrapper pointing to ~/.config/askr/.env)
      2. ~/.config/askr/.env  (global install)
      3. .env in the askr repo root (git clone dev setup)
    Anthropic API keys in those files are ignored (see _NEVER_LOAD).
    """
    before = {k: os.environ.get(k) for k in _NEVER_LOAD}
    try:
        path = os.environ.get("ASKR_ENV")
        if path and os.path.exists(path):
            load_dotenv(dotenv_path=path, override=True)
            return

        global_env = os.path.expanduser("~/.config/askr/.env")
        if os.path.exists(global_env):
            load_dotenv(dotenv_path=global_env, override=True)
        if _REPO_ENV.exists():
            load_dotenv(dotenv_path=_REPO_ENV, override=False)  # fills in anything missing
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
