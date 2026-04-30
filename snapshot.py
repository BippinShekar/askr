import os
import json
import time
import subprocess
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


def _changed_files_since(old_commit):
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", old_commit, "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode()
        return {f.strip() for f in out.split("\n") if f.strip()}
    except Exception:
        return None


def _count_git_changes(path):
    try:
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


def build_snapshot(full=False):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    all_files = _collect_files()

    existing_data = {}
    old_commit = None

    if not full and os.path.exists(SUMMARY_PATH) and os.path.exists(META_PATH):
        try:
            meta = json.load(open(META_PATH))
            old_commit = meta.get("commit")
            for entry in json.load(open(SUMMARY_PATH)):
                existing_data[entry.get("file")] = entry
        except Exception:
            pass

    if old_commit and existing_data:
        changed = _changed_files_since(old_commit)
        if changed is not None:
            to_summarize = [f for f in all_files if f in changed or f not in existing_data]
        else:
            to_summarize = all_files
    else:
        to_summarize = all_files

    if to_summarize:
        print(f"  summarizing {len(to_summarize)} file(s)...")

    updated = dict(existing_data)
    for path in to_summarize:
        updated[path] = summarize_file(path)

    all_file_set = set(all_files)
    data = [entry for path, entry in updated.items() if path in all_file_set]

    _, reverse_graph = build_graph(all_files)
    git_freq = {f: _count_git_changes(f) for f in all_files}
    for entry in data:
        entry["_score"] = _score(entry, reverse_graph, git_freq)

    data.sort(key=lambda x: x["_score"], reverse=True)

    with open(SUMMARY_PATH, "w") as f:
        json.dump(data, f, indent=2)

    graph, _ = build_graph(all_files)
    with open(GRAPH_PATH, "w") as f:
        json.dump(graph, f, indent=2)

    try:
        commit = get_last_commit()
    except Exception:
        commit = "unknown"

    with open(META_PATH, "w") as f:
        json.dump({"commit": commit, "timestamp": time.time(), "files": len(all_files)}, f)

    return len(to_summarize)


def snapshot_is_stale():
    if not os.path.exists(META_PATH) or not os.path.exists(SUMMARY_PATH):
        return True
    meta = json.load(open(META_PATH))
    try:
        if meta.get("commit") != get_last_commit():
            return True
    except Exception:
        pass
    return time.time() - meta.get("timestamp", 0) > 86400
