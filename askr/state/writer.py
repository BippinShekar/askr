import os
import json as _json
import fcntl
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from askr.state.config import load_developer, state_path, ensure_state_dir


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@contextmanager
def file_lock(path: str, timeout: float = 5.0):
    """Exclusive advisory lock on `path` using a .lock sidecar file.

    Holds the lock for the duration of the `with` block. Auto-released if the
    process dies. Degrades gracefully (yields anyway) if locking fails.
    """
    lock_path = path + ".lock"
    try:
        os.makedirs(os.path.dirname(lock_path) or ".", exist_ok=True)
        lf = open(lock_path, "w")
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(lf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    break  # timeout: proceed anyway, prefer data over deadlock
                time.sleep(0.05)
        try:
            yield
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)
            lf.close()
    except Exception:
        yield


def _read(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return ""


def _write(path: str, content: str):
    ensure_state_dir()
    with file_lock(path):
        with open(path, "w") as f:
            f.write(content)


def _handover_json_to_md(data: dict, developer: str = "") -> str:
    """Convert JSON handover to human-readable markdown (derived copy only)."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    dev = developer or data.get("session_metadata", {}).get("developer", "")
    lines = [f"# Handover: {dev}\n\nLast updated: {ts}\n\n*Source of truth: `handover_{dev}.json`*\n"]

    if data.get("task"):
        lines.append(f"## Task\n{data['task']}")
    if data.get("discussion_summary"):
        lines.append(f"## Discussion\n{data['discussion_summary']}")
    if data.get("accomplishments"):
        items = [f"- {'[x]' if a.get('done') else '[ ]'} {a['what']}" for a in data["accomplishments"]]
        lines.append("## Accomplishments\n" + "\n".join(items))
    if data.get("in_progress"):
        items = [
            f"- `{ip['file']}`" + (f" (line {ip['last_line']})" if ip.get("last_line") else "") + f": {ip['what']}"
            for ip in data["in_progress"]
        ]
        lines.append("## In Progress\n" + "\n".join(items))
    if data.get("next_actions"):
        items = []
        for a in sorted(data["next_actions"], key=lambda x: x.get("order", 99)):
            why = f"\n   *Why: {a['why']}*" if a.get("why") else ""
            items.append(f"{a.get('order', '')}. {a['action']}{why}")
        lines.append("## Next Actions\n" + "\n".join(items))
    if data.get("decisions"):
        items = [
            f"- {d['decision']}" + (f" — {d['reason']}" if d.get("reason") else "")
            for d in data["decisions"]
        ]
        lines.append("## Decisions\n" + "\n".join(items))
    if data.get("user_rejected_decisions"):
        items = [
            f"- **{r['what_was_proposed']}** — \"{r.get('user_signal', '')}\" (domain: {r.get('domain', '')})"
            for r in data["user_rejected_decisions"]
        ]
        lines.append("## User-Rejected Approaches\n" + "\n".join(items))
    if data.get("failed_approaches"):
        items = [
            f"- {f['approach']}" + (f" — {f['reason']}" if f.get("reason") else "")
            for f in data["failed_approaches"]
        ]
        lines.append("## Failed Approaches\n" + "\n".join(items))
    if data.get("files_in_play"):
        lines.append("## Files In Play\n" + "\n".join(f"- `{f}`" for f in data["files_in_play"]))
    if data.get("relational_files"):
        items = [
            f"- `{r['file']}` ({r.get('relationship', 'related')}): {r.get('why', '')}"
            for r in data["relational_files"]
        ]
        lines.append("## Relational Files\n" + "\n".join(items))
    if data.get("uncommitted_files"):
        lines.append("## Uncommitted Files\n" + "\n".join(f"- `{f}`" for f in data["uncommitted_files"]))
    if data.get("blockers"):
        lines.append("## Blockers\n" + "\n".join(f"- {b}" for b in data["blockers"]))

    return "\n\n".join(lines) + "\n"


def write_handover(content, developer: str = None, state_dir: str = None) -> str:
    dev = developer or load_developer()
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)
        _path = lambda name: os.path.join(state_dir, name)
    else:
        ensure_state_dir()
        _path = state_path

    if isinstance(content, dict):
        content.setdefault("session_metadata", {})["developer"] = dev

        json_path = _path(f"handover_{dev}.json")
        with open(json_path, "w") as f:
            _json.dump(content, f, indent=2)

        md_path = _path(f"handover_{dev}.md")
        with open(md_path, "w") as f:
            f.write(_handover_json_to_md(content, dev))

        return json_path
    else:
        # Fallback: legacy markdown path
        path = _path(f"handover_{dev}.md")
        _write(path, f"# Handover: {dev}\n\nLast updated: {_now()}\n\n{str(content).strip()}\n")
        return path


def scratch_handover_path(developer: str, session_id: str, state_dir: str = None) -> str:
    """Per-session scratch handover path — the per-turn light write's target,
    not the shared canonical handover_<dev>.json/.md. See writer/checkpoint
    docs for the 2026-07-16 fix this supports: create_handover_only() runs on
    EVERY turn of EVERY concurrently-active session and used to write straight
    to the shared file, so N sessions x M turns each meant the canonical
    handover flip-flopped between sessions' content constantly, with no
    merge — confirmed in production as a degraded, single-session handover
    hiding 21 uncommitted files' worth of sibling sessions' work. Scratch
    files are per-session so no session can ever clobber another's; the
    canonical file is only ever written by the smart-merge step in
    create_checkpoint(), which reads every fresh sibling scratch before
    writing."""
    _path = (lambda name: os.path.join(state_dir, name)) if state_dir else state_path
    return _path(f"handover_{developer}_{session_id}.scratch.json")


def write_session_scratch_handover(content: dict, developer: str, session_id: str, state_dir: str = None) -> str:
    """Write this session's own latest handover-shaped summary to its scratch
    file — JSON only, nobody reads this directly, it's staging for the next
    smart-merge. Same atomic temp-file + os.replace() pattern as the rest of
    askr's JSON state writes (commit 9e8828b) so a concurrent merge read never
    sees a half-written file."""
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)
    else:
        ensure_state_dir()
    path = scratch_handover_path(developer, session_id, state_dir)
    tmp_path = f"{path}.tmp.{os.getpid()}"
    with open(tmp_path, "w") as f:
        _json.dump(content, f, indent=2)
    os.replace(tmp_path, path)
    return path


def load_fresh_sibling_scratches(developer: str, exclude_session_id: str, state_dir: str = None,
                                  max_age_secs: int = 3600) -> list:
    """
    Every OTHER session's scratch handover that's still fresh enough to be
    worth merging — the smart-merge step in create_checkpoint() reads these
    alongside the current canonical handover so a real trigger (context,
    quota, or idle — now independently evaluated per session, see
    lifecycle._evaluate_session_triggers) incorporates ALL concurrently
    active sessions' work, not just whichever one happened to fire the
    trigger. max_age_secs default (1h) is generous — a scratch file older
    than that belongs to a session that's genuinely gone, not just idle for
    one poll cycle.
    """
    import glob
    _dir = state_dir or os.path.dirname(state_path("."))
    pattern = os.path.join(_dir, f"handover_{developer}_*.scratch.json")
    now = time.time()
    results = []
    for path in glob.glob(pattern):
        if path.endswith(f"handover_{developer}_{exclude_session_id}.scratch.json"):
            continue
        try:
            if now - os.path.getmtime(path) > max_age_secs:
                continue
            with open(path) as f:
                results.append(_json.load(f))
        except Exception:
            continue
    return results


def cleanup_stale_scratches(developer: str, state_dir: str = None, max_age_secs: int = 3600) -> int:
    """Delete scratch handovers whose owning session has been gone longer than
    max_age_secs. Called opportunistically from the merge step — cheap, and
    keeps askr_state/ from accumulating dead scratch files forever. Returns
    the number of files removed."""
    import glob
    _dir = state_dir or os.path.dirname(state_path("."))
    pattern = os.path.join(_dir, f"handover_{developer}_*.scratch.json")
    now = time.time()
    removed = 0
    for path in glob.glob(pattern):
        try:
            if now - os.path.getmtime(path) > max_age_secs:
                os.remove(path)
                removed += 1
        except Exception:
            continue
    return removed


def write_current_task(objective: str, developer: str = None):
    dev = developer or load_developer()
    path = state_path(f"current_task_{dev}.md")
    _write(path, f"# Current Task: {dev}\n\nLast updated: {_now()}\n\n## Objective\n\n{objective.strip()}\n")


def append_implementation_entry(entry_type: str, detail: str, developer: str = None, session_id: str = None):
    """Append one structured action to the developer's implementation log.

    JSONL, one file per developer — union-merge safe across concurrent pushes,
    filterable by type/session_id without parsing markdown sections.
    """
    dev = developer or load_developer()
    path = state_path(f"implementation_{dev}.jsonl")
    ensure_state_dir()

    entry = {
        "ts": _now_iso(),
        "session_id": session_id,
        "type": entry_type,
        "detail": detail,
    }
    with file_lock(path):
        with open(path, "a") as f:
            f.write(_json.dumps(entry) + "\n")


def update_architecture(content: str):
    path = state_path("architecture.md")
    _write(path, f"# Architecture\n\nLast updated: {_now()}\n\n{content.strip()}\n")


def update_blockers(content: str):
    path = state_path("blockers.md")
    _write(path, f"# Blockers\n\nLast updated: {_now()}\n\n{content.strip()}\n")
