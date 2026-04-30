import os, json
from config import SNAPSHOT_DIR

def load_fast_context():
    ctx = ""
    for f in ["README.md", "CLAUDE.md"]:
        if os.path.exists(f):
            ctx += open(f).read()[:1000] + "\n"
    return ctx

def load_snapshot():
    path = f"{SNAPSHOT_DIR}/summary.json"
    if not os.path.exists(path):
        return []
    return json.load(open(path))