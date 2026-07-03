import os
import json
import time
import pathspec
from concurrent.futures import ThreadPoolExecutor, as_completed
from askr.utils.config import SNAPSHOT_DIR
from askr.clients.claude import call_claude
from askr.qa.graph import build_graph
from askr.utils.git_utils import get_last_commit

SKIP_DIRS = {"venv", "node_modules", ".git", "__pycache__", "dist", "build", ".llm_snapshot"}
META_PATH = f"{SNAPSHOT_DIR}/meta.json"
SUMMARY_PATH = f"{SNAPSHOT_DIR}/summary.json"
GRAPH_PATH = f"{SNAPSHOT_DIR}/graph.json"
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h"}
MAX_WORKERS = 6


def _load_gitignore_spec():
    """.gitignore-matched files are skipped when building the codebase snapshot —
    otherwise gitignored files (which can include secrets, generated output, or
    anything else a developer deliberately excluded from the repo) get read and
    sent to the LLM as context."""
    try:
        with open(".gitignore") as f:
            lines = f.readlines()
        return pathspec.PathSpec.from_lines("gitwildmatch", lines)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _collect_files():
    spec = _load_gitignore_spec()
    found = []
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        if spec is not None:
            dirs[:] = [d for d in dirs
                       if not spec.match_file(os.path.relpath(os.path.join(root, d), ".") + "/")]
        for f in files:
            if os.path.splitext(f)[1] not in EXTENSIONS:
                continue
            path = os.path.join(root, f)
            if spec is not None:
                rel = os.path.relpath(path, ".")
                if spec.match_file(rel):
                    continue
            found.append(path)
    return found


def _changed_files_since(old_commit):
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "diff", "--name-only", old_commit, "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode()
        return {os.path.join(".", f.strip()) for f in out.split("\n") if f.strip()}
    except Exception:
        return None


def _count_git_changes(path):
    try:
        import subprocess
        out = subprocess.check_output(
            ["git", "log", "--oneline", path], stderr=subprocess.DEVNULL
        ).decode()
        return len([line for line in out.strip().split("\n") if line])
    except Exception:
        return 0


def _parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def _summarize_file(path):
    content = open(path, "r", errors="ignore").read()[:2000]
    prompt = f"""Summarize this file in JSON with keys: file, purpose, key_components (list), dependencies (list), importance_score (0-10).
Return only valid JSON, no markdown.

{content}"""
    res = call_claude("Return only valid JSON. No markdown.", prompt)
    try:
        data = _parse_json(res)
        data["file"] = path
        return path, data
    except Exception:
        return path, {"file": path, "purpose": "", "importance_score": 5}


def _score(entry, reverse_graph, git_freq):
    llm_score = entry.get("importance_score", 5) / 10
    centrality = len(reverse_graph.get(entry.get("file", ""), [])) / 10
    git_score = min(git_freq.get(entry.get("file", ""), 0), 20) / 20
    is_entry = 1 if entry.get("file", "").endswith(("main.py", "ask.py", "index.ts", "index.js")) else 0
    return 0.5 * llm_score + 0.2 * centrality + 0.2 * git_score + 0.1 * is_entry


def build_snapshot(full=False, show_progress=False):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    all_files = _collect_files()

    existing_data = {}
    old_commit = None

    if not full and os.path.exists(SUMMARY_PATH) and os.path.exists(META_PATH):
        try:
            with open(META_PATH) as f:
                meta = json.load(f)
            old_commit = meta.get("commit")
            with open(SUMMARY_PATH) as f:
                for entry in json.load(f):
                    existing_data[entry.get("file")] = entry
        except Exception:
            pass

    if old_commit and existing_data:
        changed = _changed_files_since(old_commit)
        to_summarize = [f for f in all_files if changed is None or f in changed or f not in existing_data]
    else:
        to_summarize = all_files

    updated = dict(existing_data)

    if to_summarize:
        if show_progress:
            from askr.utils.display import make_progress_bar
            progress, task = make_progress_bar(len(to_summarize))
            with progress:
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                    futures = {pool.submit(_summarize_file, p): p for p in to_summarize}
                    for future in as_completed(futures):
                        path, data = future.result()
                        updated[path] = data
                        progress.advance(task)
        else:
            from askr.utils.display import print_progress
            print_progress(f"  summarizing {len(to_summarize)} file(s)...")
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
                for path, data in pool.map(_summarize_file, to_summarize):
                    updated[path] = data

    all_file_set = set(all_files)
    data = [entry for path, entry in updated.items() if path in all_file_set]

    graph, reverse_graph = build_graph(all_files)
    git_freq = {f: _count_git_changes(f) for f in all_files}
    for entry in data:
        entry["_score"] = _score(entry, reverse_graph, git_freq)

    data.sort(key=lambda x: x["_score"], reverse=True)

    with open(SUMMARY_PATH, "w") as f:
        json.dump(data, f, indent=2)
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
    with open(META_PATH) as f:
        meta = json.load(f)
    try:
        if meta.get("commit") != get_last_commit():
            return True
    except Exception:
        pass
    return time.time() - meta.get("timestamp", 0) > 86400
