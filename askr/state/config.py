import os
import json

CONFIG_PATH = os.path.expanduser("~/.config/askr/config.json")
STATE_DIR = "askr_state"


def load_developer() -> str:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f).get("developer", "dev")
    return "dev"


def save_developer(name: str):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    data = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            data = json.load(f)
    data["developer"] = name
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def state_path(filename: str) -> str:
    return os.path.join(STATE_DIR, filename)


def ensure_state_dir():
    os.makedirs(STATE_DIR, exist_ok=True)
