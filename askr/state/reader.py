import os
import re as _re
import glob
import math as _math
import json as _json
from collections import Counter as _Counter
from askr.state.config import load_developer, state_path


def _read(path: str) -> str:
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return ""


def _format_handover_for_context(data: dict) -> str:
    """Format JSON handover as a targeted, Claude-readable context string."""
    parts = []

    if data.get("task"):
        parts.append(f"## Task\n{data['task']}")
    if data.get("discussion_summary"):
        parts.append(f"## What Was Discussed\n{data['discussion_summary']}")
    if data.get("in_progress"):
        items = [
            f"- {ip['file']}" + (f" (line {ip['last_line']})" if ip.get("last_line") else "") + f": {ip['what']}"
            for ip in data["in_progress"]
        ]
        parts.append("## In Progress — pick up here\n" + "\n".join(items))
    if data.get("next_actions"):
        actions = sorted(data["next_actions"], key=lambda x: x.get("order", 99))
        items = [
            f"{a.get('order', i+1)}. {a['action']}" + (f" — {a['why']}" if a.get("why") else "")
            for i, a in enumerate(actions)
        ]
        parts.append("## Next Actions (in order)\n" + "\n".join(items))
    if data.get("user_rejected_decisions"):
        items = [
            f"- DO NOT propose: {r['what_was_proposed']} (domain: {r.get('domain', 'general')})"
            for r in data["user_rejected_decisions"]
            if r.get("confidence", 0) >= 0.7
        ]
        if items:
            parts.append("## User Has Rejected These — do not re-propose\n" + "\n".join(items))
    if data.get("decisions"):
        items = [f"- {d['decision']}" for d in data["decisions"]]
        parts.append("## Settled Decisions\n" + "\n".join(items))
    if data.get("failed_approaches"):
        items = [f"- {f['approach']}: {f.get('reason', '')}" for f in data["failed_approaches"]]
        parts.append("## Failed Approaches\n" + "\n".join(items))
    if data.get("uncommitted_files"):
        parts.append(
            "## Uncommitted Files (in-flight — do not re-implement)\n"
            + "\n".join(f"- {f}" for f in data["uncommitted_files"])
        )
    if data.get("blockers"):
        parts.append("## Blockers\n" + "\n".join(f"- {b}" for b in data["blockers"]))
    if data.get("files_in_play"):
        parts.append("## Files In Play\n" + "\n".join(f"- {f}" for f in data["files_in_play"]))
    if data.get("relational_files"):
        items = [
            f"- {r['file']} ({r.get('relationship', '')}): {r.get('why', '')}"
            for r in data["relational_files"]
        ]
        parts.append("## Related Files\n" + "\n".join(items))

    return "\n\n".join(parts)


def load_own_handover(developer: str = None) -> str:
    dev = developer or load_developer()

    # JSON first (Phase 3.11+)
    json_path = state_path(f"handover_{dev}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                data = _json.load(f)
            return _format_handover_for_context(data)
        except Exception:
            pass

    # Fallback: legacy .md
    return _read(state_path(f"handover_{dev}.md"))


def load_own_handover_raw(developer: str = None) -> dict | str:
    """Return raw handover data — dict if JSON exists, str if only .md."""
    dev = developer or load_developer()
    json_path = state_path(f"handover_{dev}.json")
    if os.path.exists(json_path):
        try:
            with open(json_path) as f:
                return _json.load(f)
        except Exception:
            pass
    return _read(state_path(f"handover_{dev}.md"))


def load_team_handovers(developer: str = None) -> str:
    dev = developer or load_developer()
    parts = []

    for path in sorted(glob.glob(state_path("handover_*.json"))):
        other_dev = os.path.basename(path).replace("handover_", "").replace(".json", "")
        if other_dev == dev:
            continue
        try:
            with open(path) as f:
                data = _json.load(f)
            parts.append(f"=== {other_dev} handover ===\n{_format_handover_for_context(data)}")
        except Exception:
            pass

    # Also pick up any .md-only handovers (legacy / other devs not yet on 3.11)
    for path in sorted(glob.glob(state_path("handover_*.md"))):
        other_dev = os.path.basename(path).replace("handover_", "").replace(".md", "")
        if other_dev == dev:
            continue
        json_path = state_path(f"handover_{other_dev}.json")
        if os.path.exists(json_path):
            continue  # already loaded above
        content = _read(path)
        if content:
            parts.append(f"=== {other_dev} handover ===\n{content}")

    return "\n\n".join(parts)


def load_decisions(last_n: int = 20) -> str:
    path = state_path("decisions.jsonl")
    if not os.path.exists(path):
        return ""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = _json.loads(line)
                text = f"[{d.get('at','')}] [{d.get('dev','')}] {d.get('decision','')}"
                if d.get("reason"):
                    text += f". Reason: {d['reason']}"
                entries.append(text)
            except Exception:
                pass
    return "\n".join(entries[-last_n:])


def load_implementation_log(developer: str = None, type_filter: str = None, limit: int = 50) -> str:
    """Read a developer's structured implementation log, optionally filtered by entry type."""
    dev = developer or load_developer()
    path = state_path(f"implementation_{dev}.jsonl")
    if not os.path.exists(path):
        return ""
    entries = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = _json.loads(line)
                if type_filter and e.get("type") != type_filter:
                    continue
                entries.append(e)
            except Exception:
                pass
    lines = []
    for e in entries[-limit:]:
        sess = f" [{e['session_id'][:8]}]" if e.get("session_id") else ""
        lines.append(f"- [{e.get('ts', '')}]{sess} {e.get('type', '')}: {e.get('detail', '')}")
    return "\n".join(lines)


def load_architecture() -> str:
    return _read(state_path("architecture.md"))


def load_failed_approaches() -> list[str]:
    """Full cumulative append-only log of technical dead ends (not user
    rejections — that's rejected_decisions.jsonl). Never wired into context
    injection before Phase 3.15 — the file existed and was populated but
    nothing read it back. Returns the full list; callers rank/slice as
    needed (see _format_failed_approaches)."""
    path = state_path("failed_approaches.md")
    try:
        with open(path) as f:
            return [l.strip("- ").strip() for l in f if l.strip().startswith("-")]
    except Exception:
        return []


def load_rejected_decisions() -> list[dict]:
    """Cumulative append-only log of proposals the user explicitly rejected
    (Phase 3.13). Returns [] if the file doesn't exist yet — this function
    must work whether or not that phase has landed."""
    path = state_path("rejected_decisions.jsonl")
    entries = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(_json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return entries


def _load_snapshot_entries() -> dict:
    """file path -> snapshot entry (purpose/key_components/dependencies) from
    .llm_snapshot/summary.json, or {} if no snapshot exists yet (Phase 3.14
    isn't built — this degrades to bare file paths rather than blocking on it,
    per roadmap.md's Phase 3.15 S2 note)."""
    try:
        from askr.utils.config import SNAPSHOT_DIR
        with open(os.path.join(SNAPSHOT_DIR, "summary.json")) as f:
            entries = _json.load(f)
        return {e.get("file"): e for e in entries if e.get("file")}
    except Exception:
        return {}


_TOKEN_RE = _re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 2]


def _tfidf_rank(query: str, documents: list[str], top_n: int) -> list[int]:
    """Indices of the top_n documents most relevant to query, via a minimal
    from-scratch TF-IDF — no new dependency for what's typically a corpus of
    a few dozen short strings (decisions, failed approaches). Falls back to
    the most-recent top_n (documents are assumed oldest-first) when the query
    is empty or nothing scores above zero, rather than returning nothing."""
    n = len(documents)
    if n == 0:
        return []
    recency_fallback = list(range(max(0, n - top_n), n))[::-1]
    query_tokens = set(_tokenize(query))
    if not query_tokens:
        return recency_fallback

    doc_tokens = [_tokenize(d) for d in documents]
    df: _Counter = _Counter()
    for tokens in doc_tokens:
        for t in set(tokens):
            df[t] += 1

    scored = []
    for i, tokens in enumerate(doc_tokens):
        if not tokens:
            continue
        tf = _Counter(tokens)
        score = 0.0
        for qt in query_tokens:
            if qt in tf:
                idf = _math.log((n + 1) / (df.get(qt, 0) + 1)) + 1
                score += (tf[qt] / len(tokens)) * idf
        if score > 0:
            scored.append((score, i))

    if not scored:
        return recency_fallback
    scored.sort(key=lambda x: x[0], reverse=True)
    return [i for _, i in scored[:top_n]]


def _format_targeted_files(files_in_play: list, relational_files: list, snapshot: dict) -> str:
    """Compact section for files_in_play + relational_files, pulling snapshot
    purpose text when available (Phase 3.14), falling back to a bare path."""
    lines = []
    seen = set()
    for f in files_in_play or []:
        if not f or f in seen:
            continue
        seen.add(f)
        entry = snapshot.get(f)
        purpose = f" — {entry['purpose']}" if entry and entry.get("purpose") else ""
        lines.append(f"- {f}{purpose}")
    for r in relational_files or []:
        f = r.get("file") if isinstance(r, dict) else str(r)
        if not f or f in seen:
            continue
        seen.add(f)
        rel = r.get("relationship", "") if isinstance(r, dict) else ""
        why = r.get("why", "") if isinstance(r, dict) else ""
        entry = snapshot.get(f)
        purpose = f" — {entry['purpose']}" if entry and entry.get("purpose") else ""
        label = f" ({rel})" if rel else ""
        note = f" [{why}]" if why else ""
        lines.append(f"- {f}{label}{purpose}{note}")
    return "\n".join(lines)


_CONTEXT_BUDGET_TOKENS = 30000  # ~15% of a 200k window


def _estimate_tokens(text: str) -> int:
    return len(text) // 4  # standard rough chars-per-token heuristic, no tokenizer dependency


def _apply_budget(always: list[str], prioritized: list[tuple[str, str]]) -> list[str]:
    """always: sections included unconditionally (own handover, targeted files,
    team handovers, blockers — the core "what am I working on" signal).
    prioritized: (label, text) pairs in priority order (highest first — per
    roadmap.md Phase 3.15 S6: rejections > decisions > architecture > failed
    approaches), trimmed from the LOWEST-priority end first if the total
    exceeds _CONTEXT_BUDGET_TOKENS. Truncating blindly (old behavior: just cut
    characters) can sever a section mid-sentence; dropping whole low-priority
    sections instead keeps whatever survives coherent."""
    used = sum(_estimate_tokens(s) for s in always)
    kept = []
    for label, text in prioritized:
        if not text:
            continue
        cost = _estimate_tokens(text)
        if used + cost > _CONTEXT_BUDGET_TOKENS:
            continue
        kept.append(text)
        used += cost
    return always + kept


def load_blockers(developer: str = None) -> str:
    """Aggregate active blockers across all devs' handover JSON (race-free,
    one file per dev) plus the manually-edited blockers.md (rare, human-authored)."""
    dev = developer or load_developer()
    parts = []

    for path in sorted(glob.glob(state_path("handover_*.json"))):
        other_dev = os.path.basename(path).replace("handover_", "").replace(".json", "")
        try:
            with open(path) as f:
                data = _json.load(f)
        except Exception:
            continue
        blockers = data.get("blockers") or []
        if blockers:
            who = "you" if other_dev == dev else other_dev
            parts.append(f"- ({who}) " + "; ".join(blockers))

    manual = _read(state_path("blockers.md"))
    if manual:
        parts.append(manual)

    return "\n".join(parts)


def load_relevant_decisions(query: str, top_n: int = 10) -> str:
    """Decisions ranked by TF-IDF relevance to query (handover task +
    next_actions), not just the most recent N (Phase 3.15 S3) — a decision
    made 40 sessions ago about the exact file being touched now is more
    useful than one made yesterday about something unrelated. Falls back to
    the most-recent top_n when nothing scores above zero (see _tfidf_rank)."""
    path = state_path("decisions.jsonl")
    if not os.path.exists(path):
        return ""
    raw = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                raw.append(_json.loads(line))
            except Exception:
                pass
    if not raw:
        return ""
    doc_texts = [f"{d.get('decision','')} {d.get('reason','')}" for d in raw]
    idxs = sorted(_tfidf_rank(query, doc_texts, top_n))
    lines = []
    for i in idxs:
        d = raw[i]
        text = f"[{d.get('at','')}] [{d.get('dev','')}] {d.get('decision','')}"
        if d.get("reason"):
            text += f". Reason: {d['reason']}"
        lines.append(text)
    return "\n".join(lines)


def _format_rejected_decisions(files_in_play: list, relational_files: list) -> str:
    """Rejected proposals whose domain matches an in-play or relational file
    (Phase 3.15 S4). Empty string if Phase 3.13 hasn't populated the file yet
    or nothing matches this session's scope — never errors either way."""
    entries = load_rejected_decisions()
    if not entries:
        return ""
    scope = {f for f in (files_in_play or []) if f}
    for r in relational_files or []:
        f = r.get("file") if isinstance(r, dict) else str(r)
        if f:
            scope.add(f)
    if not scope:
        return ""
    matched = [
        e for e in entries
        if e.get("domain") and any(e["domain"] in f or f in e["domain"] for f in scope)
    ]
    if not matched:
        return ""
    return "\n".join(
        f"- DO NOT propose: {e.get('what_was_proposed','')} (domain: {e.get('domain','')})"
        for e in matched
    )


def _format_failed_approaches(query: str) -> str:
    """Failed approaches semantically matched to the current task, plus the
    last 3 as a recency floor regardless of relevance score (Phase 3.15 S5) —
    the honest-risk note in roadmap.md calls this out explicitly: a recent
    dead end is worth surfacing even if it doesn't lexically match the task."""
    all_items = load_failed_approaches()
    if not all_items:
        return ""
    recency_floor = set(range(max(0, len(all_items) - 3), len(all_items)))
    ranked = set(_tfidf_rank(query, all_items, top_n=5))
    idxs = sorted(recency_floor | ranked)
    return "\n".join(f"- {all_items[i]}" for i in idxs)


def build_context_injection(developer: str = None) -> str:
    dev = developer or load_developer()

    own_handover_raw = load_own_handover_raw(dev)
    own_handover = load_own_handover(dev)
    team_handovers = load_team_handovers(dev)
    blockers = load_blockers(dev)

    files_in_play, relational_files, query = [], [], ""
    if isinstance(own_handover_raw, dict):
        files_in_play = own_handover_raw.get("files_in_play") or []
        relational_files = own_handover_raw.get("relational_files") or []
        next_actions_text = " ".join(
            (a.get("action", "") if isinstance(a, dict) else str(a))
            for a in (own_handover_raw.get("next_actions") or [])
        )
        query = f"{own_handover_raw.get('task', '')} {next_actions_text}".strip()

    sections = []
    if own_handover:
        sections.append(f"YOUR LAST SESSION HANDOVER:\n{own_handover}")

    if not files_in_play and not relational_files:
        # S7 fallback: no targeting signal yet (e.g. the very first session,
        # or a handover predating Phase 3.11's files_in_play field) — revert
        # to the full, untargeted dump this mode replaces.
        if team_handovers:
            sections.append(f"TEAM HANDOVERS:\n{team_handovers}")
        decisions = load_decisions()
        if decisions:
            sections.append(f"RECENT DECISIONS:\n{decisions}")
        architecture = load_architecture()
        if architecture:
            sections.append(f"ARCHITECTURE:\n{architecture}")
        if blockers:
            sections.append(f"UNIVERSAL BLOCKERS (affect whole team):\n{blockers}")
        if not sections:
            return ""
        return "=== ASKR PROJECT STATE ===\n\n" + "\n\n---\n\n".join(sections) + "\n\n=== END STATE ==="

    # Targeted mode (Phase 3.15): files_in_play/relational_files drive what
    # gets pulled in, instead of dumping every state file in full every time.
    snapshot = _load_snapshot_entries()
    targeted = _format_targeted_files(files_in_play, relational_files, snapshot)
    if targeted:
        sections.append(f"RELEVANT FILES (in play + related):\n{targeted}")
    if team_handovers:
        sections.append(f"TEAM HANDOVERS:\n{team_handovers}")
    if blockers:
        sections.append(f"UNIVERSAL BLOCKERS (affect whole team):\n{blockers}")

    rejected = _format_rejected_decisions(files_in_play, relational_files)
    relevant_decisions = load_relevant_decisions(query, top_n=10)
    architecture = load_architecture()
    failed = _format_failed_approaches(query)

    prioritized_raw = [
        f"REJECTED — DO NOT RE-PROPOSE:\n{rejected}" if rejected else "",
        f"RELEVANT DECISIONS:\n{relevant_decisions}" if relevant_decisions else "",
        f"ARCHITECTURE:\n{architecture}" if architecture else "",
        f"FAILED APPROACHES (relevant + recent):\n{failed}" if failed else "",
    ]
    prioritized = [(str(i), t) for i, t in enumerate(prioritized_raw) if t]

    parts = _apply_budget(sections, prioritized)
    if not parts:
        return ""
    return "=== ASKR PROJECT STATE ===\n\n" + "\n\n---\n\n".join(parts) + "\n\n=== END STATE ==="
