import os
from pathlib import Path
from dotenv import load_dotenv

# .env next to the repo root (two levels up from askr/utils/env.py)
_REPO_ENV = Path(__file__).parent.parent.parent / ".env"


def load():
    """
    Load API keys in priority order:
      1. ASKR_ENV env var (set by brew wrapper pointing to ~/.config/askr/.env)
      2. ~/.config/askr/.env  (global install)
      3. .env in the askr repo root (git clone dev setup)
    """
    path = os.environ.get("ASKR_ENV")
    if path and os.path.exists(path):
        load_dotenv(dotenv_path=path, override=True)
        return

    global_env = os.path.expanduser("~/.config/askr/.env")
    if os.path.exists(global_env):
        load_dotenv(dotenv_path=global_env, override=True)
    if _REPO_ENV.exists():
        load_dotenv(dotenv_path=_REPO_ENV, override=False)  # fills in anything missing
