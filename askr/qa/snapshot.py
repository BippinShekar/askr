import os
import json
import time
import subprocess
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
RDEP_PATH = f"{SNAPSHOT_DIR}/rdep.json"
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".rb", ".go", ".rs", ".java", ".kt", ".swift", ".c", ".cpp", ".h"}
MAX_WORKERS = 6

# ---------------------------------------------------------------------------
# Phase 3.14 — Incremental Snapshot as Architecture Source (roadmap.md).
# Everything from _atomic_write_json() onward extends the init-time builder
# above with a post-session incremental sync: a reverse-dependency index
# (S1/S7), batched Haiku re-summarization of changed files + their importers
# (S2/S3), delete (S4) and rename (S5) reconciliation, and a deterministic
# architecture.md renderer that replaces the old free-text Haiku regen as
# the Implementation Guard's read path (S6 support).
# ---------------------------------------------------------------------------


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


def _is_trackable_file(path: str) -> bool:
    """Same file criteria _collect_files() applies at init time (extension
    allow-list, SKIP_DIRS), applied to files that come from `git diff`
    instead of the filesystem walk. _changed_files_since() has no such
    filter of its own — without this, a non-code file in the diff (a
    binary asset, or .llm_snapshot/*.json if it were ever accidentally
    committed) would get sent to Haiku as if it were source. That's not
    just wasteful: a plausible-looking response for garbage input would
    likely still carry a non-empty `purpose`, so the empty-purpose
    discard-and-rescan safety net wouldn't catch it either."""
    if os.path.splitext(path)[1] not in EXTENSIONS:
        return False
    dir_parts = os.path.normpath(path).split(os.sep)[:-1]  # directories only, not the filename itself
    return not any(p in SKIP_DIRS or p.startswith(".") for p in dir_parts)


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

    # S1: reverse dependency index, resolved to real file paths (not just raw
    # import strings — see _resolve_import). Reuses the `graph` computed above
    # rather than re-scanning every file's imports a second time.
    save_rdep_index(build_full_rdep_index(all_files, graph=graph))

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


# ---------------------------------------------------------------------------
# Shared low-level helpers
# ---------------------------------------------------------------------------

def _atomic_write_json(path: str, data):
    """Temp-file + os.replace so a concurrent reader never observes a
    partially-written file — same pattern as askr/session/registry.py's
    _atomic_write_json (see commit 9e8828b)."""
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)


def _load_summary_dict() -> dict:
    """file -> entry, or {} if summary.json doesn't exist / is corrupt."""
    try:
        with open(SUMMARY_PATH) as f:
            return {e.get("file"): e for e in json.load(f) if e.get("file")}
    except Exception:
        return {}


def _save_summary_dict(entries_by_file: dict):
    data = list(entries_by_file.values())
    data.sort(key=lambda e: e.get("_score", 0), reverse=True)
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    from askr.state.writer import file_lock
    with file_lock(SUMMARY_PATH):
        _atomic_write_json(SUMMARY_PATH, data)


def load_rdep_index() -> dict:
    try:
        with open(RDEP_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_rdep_index(idx: dict):
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    from askr.state.writer import file_lock
    with file_lock(RDEP_PATH):
        _atomic_write_json(RDEP_PATH, idx)


# ---------------------------------------------------------------------------
# S1 / S7 — reverse dependency index
# ---------------------------------------------------------------------------

def _resolve_import(importer: str, imp: str, file_set: set) -> str | None:
    """Best-effort resolution of a raw import string (module name or relative
    path) to an actual file in `file_set`, so the reverse dependency index is
    keyed by real file paths instead of raw import strings. Handles the two
    common in-repo cases: absolute dotted Python modules, and relative
    JS/TS imports. Bare package imports (npm modules, third-party Python
    packages) resolve to None and are dropped — they're not in this repo.

    Deliberately doesn't handle dynamic requires, barrel-file re-exports, or
    runtime-resolved imports — accepted per roadmap.md's Phase 3.14
    honest-risks note: 'these gaps are acceptable, the index doesn't need to
    be perfect, just not wrong about what it does cover.'
    """
    ext = os.path.splitext(importer)[1]

    if ext == ".py":
        rel = imp.replace(".", "/")
        for candidate in (f"./{rel}.py", f"./{rel}/__init__.py"):
            if candidate in file_set:
                return candidate
        return None

    if ext in (".js", ".jsx", ".ts", ".tsx"):
        if not imp.startswith("."):
            return None  # bare package import, not an in-repo file
        base = os.path.normpath(os.path.join(os.path.dirname(importer), imp))
        base = base.replace(os.sep, "/")
        if not base.startswith("./") and not base.startswith("../"):
            base = f"./{base}"
        candidates = []
        if os.path.splitext(base)[1]:
            candidates.append(base)
        else:
            for ext2 in (".ts", ".tsx", ".js", ".jsx"):
                candidates.append(base + ext2)
            for ext2 in (".ts", ".tsx", ".js", ".jsx"):
                candidates.append(f"{base}/index{ext2}")
        for candidate in candidates:
            if candidate in file_set:
                return candidate
        return None

    return None


def _invert_graph(graph: dict, file_set: set) -> dict:
    idx: dict = {}
    for importer, imports in graph.items():
        for imp in imports:
            resolved = _resolve_import(importer, imp, file_set)
            if resolved and resolved != importer:
                idx.setdefault(resolved, [])
                if importer not in idx[resolved]:
                    idx[resolved].append(importer)
    return {k: sorted(v) for k, v in idx.items()}


def build_full_rdep_index(all_files: list, graph: dict = None) -> dict:
    """S1: full reverse-dependency index build, {file: [importer_files]}.
    Reuses a pre-built forward `graph` (build_graph's output) when the
    caller already has one — build_snapshot() does — to avoid re-scanning
    every file's imports twice."""
    file_set = set(all_files)
    if graph is None:
        graph, _ = build_graph(all_files)
    return _invert_graph(graph, file_set)


def update_rdep_index_incremental(files_to_rescan: list, all_files: set) -> dict:
    """S7: incremental update — only re-scans the import lists of
    `files_to_rescan` (rather than rebuilding the whole index from scratch
    on every batch run), removes their old outgoing edges, and merges in
    the new ones."""
    idx = load_rdep_index()
    rescan_set = set(files_to_rescan)

    for target in list(idx.keys()):
        filtered = [i for i in idx[target] if i not in rescan_set]
        if filtered:
            idx[target] = filtered
        else:
            del idx[target]

    if files_to_rescan:
        graph, _ = build_graph(list(files_to_rescan))
        fresh = _invert_graph(graph, set(all_files))
        for target, importers in fresh.items():
            idx.setdefault(target, [])
            idx[target] = sorted(set(idx[target]) | set(importers))

    save_rdep_index(idx)
    return idx


def get_importers(files, idx: dict) -> set:
    """Files whose snapshot entry is now stale because one of `files`
    (something they import) just changed — 'not optional' per roadmap.md:
    'without it, the snapshot lies.'"""
    out = set()
    for f in files:
        out.update(idx.get(f, []))
    return out


# ---------------------------------------------------------------------------
# S2 — batched Haiku update, with the two mandatory risk mitigations:
# token-count check before batching (split into <=2 calls), and
# discard-and-rescan on empty `purpose`.
# ---------------------------------------------------------------------------

_FILE_CONTENT_CHARS = 2000  # matches _summarize_file's existing per-file truncation
_TOKEN_SPLIT_THRESHOLD = 150_000  # conservative margin under Haiku's 200k window
_MAX_BATCH_SPLITS = 2


def _read_truncated(path: str) -> str:
    try:
        return open(path, "r", errors="ignore").read()[:_FILE_CONTENT_CHARS]
    except Exception:
        return ""


def _estimate_tokens(text: str) -> int:
    return len(text) // 4  # same rough chars-per-token heuristic askr/state/reader.py uses


def _split_into_batches(files: list) -> list:
    """Token-count check before batching (roadmap.md Phase 3.14 honest-risk:
    'need a token count check before batching and split into <=2 calls if
    needed'). Returns [files] unsplit when the estimated total is under
    _TOKEN_SPLIT_THRESHOLD; otherwise greedily bin-packs into 2 roughly
    balanced batches by estimated size."""
    if not files:
        return []
    sizes = {f: _estimate_tokens(_read_truncated(f)) for f in files}
    if sum(sizes.values()) <= _TOKEN_SPLIT_THRESHOLD:
        return [files]

    bins = [[] for _ in range(_MAX_BATCH_SPLITS)]
    bin_totals = [0] * _MAX_BATCH_SPLITS
    for f in sorted(files, key=lambda f: sizes[f], reverse=True):
        idx = bin_totals.index(min(bin_totals))
        bins[idx].append(f)
        bin_totals[idx] += sizes[f]
    return [b for b in bins if b]


def _build_batch_prompt(files: list) -> str:
    parts = [f'=== FILE: {f} ===\n{_read_truncated(f)}' for f in files]
    joined = "\n\n".join(parts)
    return f"""Summarize EACH of the following {len(files)} files. For each file return one JSON object with keys: file (must exactly match the path given after "=== FILE: "), purpose, key_components (list), dependencies (list), importance_score (0-10).

Return a single JSON array containing exactly one object per file, in the same order as given. Return only valid JSON, no markdown, no commentary.

{joined}"""


def _call_batch(files: list) -> str:
    prompt = _build_batch_prompt(files)
    return call_claude(
        "Return only a valid JSON array. No markdown, no commentary.",
        prompt,
        mode="snapshot_batch",
        query_preview=f"snapshot batch update: {len(files)} file(s)",
    )


def _parse_batch_response(raw: str) -> dict:
    try:
        data = _parse_json(raw)
    except Exception:
        return {}
    if not isinstance(data, list):
        return {}
    out = {}
    for item in data:
        if isinstance(item, dict) and item.get("file"):
            out[item["file"]] = item
    return out


def update_snapshot_batch(files: list) -> dict:
    """S2: send all changed files in as few Haiku calls as the token-count
    check allows (see _split_into_batches — <=2 calls), merge the results
    into summary.json.

    Risk mitigation (roadmap.md, mandatory): any entry with an empty/missing
    `purpose` after the batch — including files the batch response silently
    dropped — is discarded and individually re-scanned via _summarize_file
    rather than trusted as-is. A corrupted batch response must never
    silently poison the Implementation Guard's source of truth.

    Returns {"updated": [...], "rescanned": [...], "dropped": [...]} —
    "dropped" is files that still have no usable purpose even after the
    individual rescan, and are excluded from the snapshot entirely rather
    than stored empty.
    """
    files = [f for f in dict.fromkeys(files) if f and os.path.exists(f)]
    if not files:
        return {"updated": [], "rescanned": [], "dropped": []}

    batch_results = {}
    for batch in _split_into_batches(files):
        try:
            raw = _call_batch(batch)
            batch_results.update(_parse_batch_response(raw))
        except Exception:
            pass  # every file in this batch falls through to the rescan pass below

    updated, need_rescan = {}, []
    for f in files:
        entry = batch_results.get(f)
        if entry and str(entry.get("purpose", "")).strip():
            entry["file"] = f
            updated[f] = entry
        else:
            need_rescan.append(f)

    rescanned, dropped = [], []
    for f in need_rescan:
        _, data = _summarize_file(f)
        if str(data.get("purpose", "")).strip():
            data["file"] = f
            updated[f] = data
            rescanned.append(f)
        else:
            dropped.append(f)

    if updated:
        existing = _load_summary_dict()
        for f, entry in updated.items():
            old = existing.get(f)
            entry["_score"] = old.get("_score") if old and "_score" in old else entry.get("importance_score", 5) / 10
            existing[f] = entry
        _save_summary_dict(existing)

    return {"updated": list(updated.keys()), "rescanned": rescanned, "dropped": dropped}


# ---------------------------------------------------------------------------
# S4 — deleted files
# ---------------------------------------------------------------------------

def prune_deleted_entries() -> list:
    """S4: remove snapshot entries (and their rdep index traces) for files
    no longer present in the repo. Returns the list of removed file paths.

    Uses a direct filesystem check (os.path.exists), not `git ls-files`
    (the roadmap's suggested mechanism) — verified `git ls-files` still
    lists a file that's been deleted from the working tree but not yet
    staged/committed (it reflects the index, not disk), which would leave a
    stale entry pointing at content that no longer exists. os.path.exists
    has no such gap, and — same as the git-ls-files approach would have —
    never prunes a brand-new file that exists on disk but isn't tracked or
    committed yet."""
    existing = _load_summary_dict()
    removed = [f for f in existing if not os.path.exists(f)]
    if not removed:
        return []
    for f in removed:
        del existing[f]
    _save_summary_dict(existing)

    idx = load_rdep_index()
    changed = False
    removed_set = set(removed)
    for f in removed:
        if f in idx:
            del idx[f]
            changed = True
    for target in list(idx.keys()):
        filtered = [i for i in idx[target] if i not in removed_set]
        if len(filtered) != len(idx[target]):
            idx[target] = filtered
            changed = True
    if changed:
        save_rdep_index(idx)
    return removed


# ---------------------------------------------------------------------------
# S5 — renamed files
# ---------------------------------------------------------------------------

_RENAME_CONTENT_CHANGED_THRESHOLD = 100  # git similarity score; <100 means content changed too


def _git_renames_since(old_ref: str, new_ref: str = "HEAD") -> list:
    """[(old_path, new_path, similarity_score)] via `git diff --name-status
    -M` — explicit -M so rename detection doesn't depend on the caller's
    diff.renames config."""
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-status", "-M", old_ref, new_ref],
            stderr=subprocess.DEVNULL,
        ).decode()
    except Exception:
        return []
    renames = []
    for line in out.split("\n"):
        line = line.strip()
        if not line or not line.startswith("R"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        status, old, new = parts
        try:
            score = int(status[1:]) if len(status) > 1 else 100
        except ValueError:
            score = 100
        renames.append((os.path.join(".", old), os.path.join(".", new), score))
    return renames


def apply_renames(renames: list) -> list:
    """S5: relocate a renamed file's existing snapshot entry (and rdep
    index edges) to its new path in place, preserving the LLM-generated
    purpose/history instead of treating the rename as delete+create.
    Returns the new paths whose content also changed (similarity < 100) and
    therefore still need a re-scan."""
    if not renames:
        return []
    existing = _load_summary_dict()
    idx = load_rdep_index()
    needs_rescan = []
    changed_summary = False
    changed_idx = False

    for old, new, score in renames:
        if old in existing:
            entry = existing.pop(old)
            entry["file"] = new
            existing[new] = entry
            changed_summary = True
        else:
            needs_rescan.append(new)

        if old in idx:
            idx[new] = sorted(set(idx.pop(old)) | set(idx.get(new, [])))
            changed_idx = True
        for target, importers in list(idx.items()):
            if old in importers:
                idx[target] = sorted((set(importers) - {old}) | {new})
                changed_idx = True

        if score < _RENAME_CONTENT_CHANGED_THRESHOLD:
            needs_rescan.append(new)

    if changed_summary:
        _save_summary_dict(existing)
    if changed_idx:
        save_rdep_index(idx)
    return needs_rescan


# ---------------------------------------------------------------------------
# S6 support — deterministic architecture.md rendering from snapshot entries
# ---------------------------------------------------------------------------

_CORE_IMPORTER_THRESHOLD = 3  # importers at/above this count get flagged core/shared


def render_architecture_md(entries: list) -> str:
    """Deterministic (no LLM call) architecture.md-style rendering from
    .llm_snapshot/summary.json entries. Phase 3.14 S6: this is the snapshot
    becoming the live architecture record — grouped by top-level directory,
    sorted by _score (falls back to importance_score) descending within
    each group. Files with >= _CORE_IMPORTER_THRESHOLD importers (per
    rdep.json) are tagged "core/shared" — askr/hooks/pre_tool_use.py's
    _is_shared_interface() keyword-proximity check depends on that literal
    wording appearing near the filename, so it's deliberate, not decorative.
    """
    if not entries:
        return ""
    rdep = load_rdep_index()
    groups: dict = {}
    for e in entries:
        f = e.get("file", "")
        if not f:
            continue
        stripped = f.lstrip("./")
        top = stripped.split("/", 1)[0] if "/" in stripped else "(root)"
        groups.setdefault(top, []).append(e)

    def _sort_key(e):
        return e.get("_score", e.get("importance_score", 0) / 10)

    lines = []
    for top in sorted(groups):
        lines.append(f"## {top}/")
        for e in sorted(groups[top], key=_sort_key, reverse=True):
            f = e["file"]
            purpose = str(e.get("purpose", "")).strip()
            importers = rdep.get(f, [])
            tag = f" **[core/shared — imported by {len(importers)} files]**" if len(importers) >= _CORE_IMPORTER_THRESHOLD else ""
            line = f"- `{f}`{tag}"
            if purpose:
                line += f": {purpose}"
            lines.append(line)
        lines.append("")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# S3 orchestrator — called from askr/hooks/stop.py after every turn's
# background handover.
# ---------------------------------------------------------------------------

def sync_snapshot_incremental() -> dict:
    """S3-S7 orchestrator. Diffs from the snapshot's last-synced commit
    (meta.json's `commit` field — shared with build_snapshot()'s own
    incremental logic, not re-derived) to current HEAD, rather than
    literally `HEAD~1..HEAD`: askr's own automated git commits only happen
    on the daemon's rare emergency-checkpoint path, not per-turn (see
    askr/hooks/stop.py's docstring), so most Stop-hook firings see no new
    commit at all — re-batching the same "changed" files on every single
    reply would be pure waste. When several commits do land between two
    syncs, diffing from the last-synced commit (not just HEAD~1) still
    picks up all of them, not just the latest.

    No-ops (returns {"skipped": reason}) if there's no snapshot yet, no git
    repo, or HEAD hasn't moved since the last sync.
    """
    if not os.path.exists(SUMMARY_PATH) or not os.path.exists(META_PATH):
        return {"skipped": "no snapshot yet"}

    try:
        with open(META_PATH) as f:
            meta = json.load(f)
        last_synced = meta.get("commit")
    except Exception:
        return {"skipped": "unreadable meta.json"}

    try:
        head = get_last_commit()
    except Exception:
        return {"skipped": "not a git repo / no commits"}

    if not last_synced or last_synced == "unknown" or last_synced == head:
        return {"skipped": "no new commit"}

    renames = _git_renames_since(last_synced, head)
    rename_rescan = apply_renames(renames)
    removed = prune_deleted_entries()
    removed_set = set(removed)

    changed = _changed_files_since(last_synced) or set()
    rename_old_paths = {old for old, _, _ in renames}
    renamed_new_paths = {new for _, new, _ in renames}
    changed = {f for f in changed if f not in rename_old_paths and f not in removed_set}

    idx = load_rdep_index()
    importers = get_importers(list(changed | renamed_new_paths), idx)

    to_rescan = (changed | set(rename_rescan) | importers) - removed_set
    to_rescan = sorted(f for f in to_rescan if os.path.exists(f) and _is_trackable_file(f))

    result = update_snapshot_batch(to_rescan) if to_rescan else {"updated": [], "rescanned": [], "dropped": []}

    if to_rescan:
        all_files = set(_load_summary_dict().keys())
        update_rdep_index_incremental(to_rescan, all_files)

    try:
        entries = list(_load_summary_dict().values())
        if entries:
            from askr.state.writer import update_architecture
            update_architecture(render_architecture_md(entries))
    except Exception:
        pass

    try:
        with open(META_PATH) as f:
            meta = json.load(f)
    except Exception:
        meta = {}
    meta["commit"] = head
    meta["timestamp"] = time.time()
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    _atomic_write_json(META_PATH, meta)

    result["removed"] = removed
    result["renamed"] = [{"old": o, "new": n} for o, n, _ in renames]
    return result
