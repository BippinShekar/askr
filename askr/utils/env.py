import os
from dotenv import load_dotenv


def load():
    """
    Load API keys in priority order:
      1. ASKR_ENV env var (set by brew wrapper pointing to ~/.config/askr/.env)
      2. ~/.config/askr/.env  (global install fallback)
      3. local .env           (dev / git clone)
    """
    path = os.environ.get("ASKR_ENV")
    if path and os.path.exists(path):
        load_dotenv(dotenv_path=path, override=True)
        return

    global_env = os.path.expanduser("~/.config/askr/.env")
    if os.path.exists(global_env):
        load_dotenv(dotenv_path=global_env, override=True)
    else:
        load_dotenv(override=True)
