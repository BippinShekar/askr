import os
import json
import time
from config import SNAPSHOT_DIR
from client_claude import call_claude
from graph import build_graph
from git_utils import get_last_commit

SKIP_DIRS = {"venv", "node_modules", ".git", "__pycache__", "dist", "build", ".llm_snapshot"}
META_PATH = f"{SNAPSHOT_DIR}/meta.json"
SUMMARY_PATH = f"{SNAPSHOT_DIR}/summary.json"
GRAPH_PATH = f"{SNAPSHOT_DIR}/graph.json"


def _collect_files():
    found = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            if f.endswith((".py", ".js", ".ts", ".tsx", ".jsx")):
                found.append(os.path.join(root, f))
    return found


def _count_git_changes(path):
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "log", "--oneline", path], stderr=subprocess.DEVNULL
        ).decode()
        return len([line for line in out.strip().split("\n") if line])
    except Exception:
        return 0


def summarize_file(path):
    content = open(path, "r", errors="ignore").read()[:2000]
    prompt = f"""Summarize this file in JSON with keys: file, purpose, key_components (list), dependencies (list), importance_score (0-10).
Return only valid JSON, no markdown.

{content}"""
    res = call_claude("Return only valid JSON. No markdown.", prompt)
    try:
        data = json.loads(res)
        data["file"] = path
        return data
    except Exception:
        return {"file": path, "purpose": "", "importance_score": 5}


def _score(entry, reverse_graph, git_freq):
    llm_score = entry.get("importance_score", 5) / 10
    centrality = len(reverse_graph.get(entry.get("file", ""), [])) / 10
    git_score = min(git_freq.get(entry.get("file", ""), 0), 20) / 20
    is_entry = 1 if entry.get("file", "").endswith(("main.py", "ask.py", "index.ts", "index.js")) else 0
    return 0.5 * llm_score + 0.2 * centrality + 0.2 * git_score + 0.1 * is_entry


def build_snapshot():
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    files = _collect_files()

    data = []
    for path in files:
        entry = summarize_file(path)
        data.append(entry)

    _, reverse_graph = build_graph(files)
    git_freq = {f: _count_git_changes(f) for f in files}

    for entry in data:
        entry["_score"] = _score(entry, reverse_graph, git_freq)

    data.sort(key=lambda x: x["_score"], reverse=True)

    with open(SUMMARY_PATH, "w") as f:
        json.dump(data, f, indent=2)

    graph, _ = build_graph(files)
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2)

    try:
        commit = get_last_commit()
    except Exception:
        commit = "unknown"

    with open(META_PATH, "w") as f:
        json.dump({"commit": commit, "timestamp": time.time()}, f)


def snapshot_is_stale():
    if not os.path.exists(META_PATH) or not os.path.exists(SUMMARY_PATH):
        return True
    meta = json.load(open(META_PATH))
    try:
        current_commit = get_last_commit()
        if meta.get("commit") != current_commit:
            return True
    except Exception:
        pass
    age = time.time() - meta.get("timestamp", 0)
    return age > 86400
