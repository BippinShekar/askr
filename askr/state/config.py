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


def load_voice_enabled() -> bool:
    return bool(_load_config().get("voice_notifications", False))


def save_voice_enabled(enabled: bool):
    data = _load_config()
    data["voice_notifications"] = bool(enabled)
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
    # Walk up from cwd looking for the nearest askr_state/ (same idea as git
    # walking up to find .git/) — handles running from a subdirectory of an
    # initialized project. Deliberately never falls back to a DIFFERENT
    # project's globally-stored path: that previously caused hooks firing in
    # a sibling repo with no askr_state/ anywhere in its own tree (e.g. never
    # ran `askr init` there) to silently resolve to whichever project was
    # stored globally and write cross-project state into it. Walking up can
    # only ever reach ancestors of cwd, never a sibling project, so it's safe.
    # If nothing is found anywhere up the tree, return the (nonexistent)
    # cwd-relative path — every caller already checks os.path.isdir() on the
    # result before treating askr as initialized here.
    current = os.path.abspath(os.getcwd())
    while True:
        candidate = os.path.join(current, _STATE_DIR_NAME)
        if os.path.isdir(candidate):
            return candidate
        parent = os.path.dirname(current)
        if parent == current:
            return os.path.join(os.getcwd(), _STATE_DIR_NAME)
        current = parent


def state_path(filename: str) -> str:
    return os.path.join(get_state_dir(), filename)


def ensure_state_dir():
    os.makedirs(get_state_dir(), exist_ok=True)


def _project_config_path(project_path: str = None) -> str:
    base = project_path or os.getcwd()
    return os.path.join(base, _STATE_DIR_NAME, "config.json")


def load_project_config(project_path: str = None) -> dict:
    path = _project_config_path(project_path)
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_project_config(data: dict, project_path: str = None):
    path = _project_config_path(project_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = load_project_config(project_path)
    existing.update(data)
    with open(path, "w") as f:
        json.dump(existing, f, indent=2)
