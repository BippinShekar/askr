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


def load_inventory():
    """One-liner summary of every file in the snapshot — gives LLM the full picture."""
    if not os.path.exists(SUMMARY_PATH):
        return ""
    with open(SUMMARY_PATH) as f:
        data = json.load(f)
    data.sort(key=lambda x: x.get("_score", 0), reverse=True)
    lines = [f"{d.get('file')} — {d.get('purpose', '')}" for d in data]
    return "\n".join(lines)


def load_file_contents(snapshot, chars_per_file=2500):
    """Return dict of file path → truncated content for files in snapshot."""
    contents = {}
    for entry in snapshot:
        path = entry.get("file", "")
        if path and os.path.exists(path):
            try:
                with open(path, errors="ignore") as f:
                    contents[path] = f.read(chars_per_file)
            except Exception:
                pass
    return contents
