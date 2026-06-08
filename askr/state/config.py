import os
import json

CONFIG_PATH = os.path.expanduser("~/.config/askr/config.json")
_STATE_DIR_NAME = "askr_state"


def _load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {}


def _save_config(data: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def load_developer() -> str:
    return _load_config().get("developer", "dev")


def save_developer(name: str):
    data = _load_config()
    data["developer"] = name
    _save_config(data)


def save_project_path(path: str):
    data = _load_config()
    data["project_path"] = os.path.abspath(path)
    _save_config(data)


def load_project_path() -> str:
    stored = _load_config().get("project_path", "")
    if stored and os.path.isdir(stored):
        return stored
    return os.getcwd()


def get_state_dir() -> str:
    # Prefer cwd-relative askr_state — hooks run inside Claude with the correct
    # project cwd, so this is always right for multi-repo installs.
    # Falls back to stored path for daemon/CLI calls that may run elsewhere.
    cwd_state = os.path.join(os.getcwd(), _STATE_DIR_NAME)
    if os.path.isdir(cwd_state):
        return cwd_state
    return os.path.join(load_project_path(), _STATE_DIR_NAME)


def state_path(filename: str) -> str:
    return os.path.join(get_state_dir(), filename)


def ensure_state_dir():
    os.makedirs(get_state_dir(), exist_ok=True)
