import os
import json
from config import SNAPSHOT_DIR

FAST_CTX_FILES = ["README.md", "CLAUDE.md"]
SUMMARY_PATH = f"{SNAPSHOT_DIR}/summary.json"


def load_fast_context():
    ctx = ""
    for fname in FAST_CTX_FILES:
        if os.path.exists(fname):
            with open(fname) as f:
                ctx += f.read()[:1000] + "\n"
    return ctx


def load_snapshot(top_k=6):
    if not os.path.exists(SUMMARY_PATH):
        return []
    with open(SUMMARY_PATH) as f:
        data = json.load(f)
    data.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return data[:top_k]
