#!/usr/bin/env python3
"""
Behavioral Preference Persistence (roadmap Phase 3.9).

Askr detects when a user gives an instruction that should apply to every
future session ("always build in stages", "never use emojis") and persists
it to the fenced askr:prefs section of CLAUDE.md automatically — confirmed
in Cursor via a behavior_confirm notification, or auto-persisted with a
Discord notice when headless.

This module owns:
  - reading/writing the fenced askr:prefs section in global (~/.claude/CLAUDE.md)
    and project (./CLAUDE.md) files — a NEW marker pair, deliberately separate
    from askr init's own askr:behavioral-start/end and askr:guard-start/end
    sections (cli/askr.py), which are byte-for-byte synced against a template
    and must not be touched by anything else.
  - the dedup logic that keeps already-persisted or already-pending rules from
    being re-surfaced.
  - the pending-candidate store (~/.config/askr/behavior_pending.json) so
    `askr prefs pending` can list rules that were detected but never
    confirmed (e.g. Cursor was closed mid-session).
  - the delivery mechanism: write notification.json (type=behavior_confirm)
    for the Cursor extension's Keep/Discard popup, and spawn a detached
    fallback worker that headless-persists + Discord-notifies if no IDE
    window claims the notification — mirrors lifecycle.py's
    _spawn_terminal_app_fallback / _terminal_app_fallback_worker pattern
    exactly (sleep, then check the shared notification.json's `shown` flag).

The actual LLM extraction lives in checkpoint.py's _generate_handover_with_llm
(behavioral_preferences field) — this module is deliberately LLM-free so its
dedup/persistence logic is cheap to test without mocking call_claude.
"""

import json
import os
import re

_PREFS_MARKER_START = "<!-- askr:prefs-start -->"
_PREFS_MARKER_END   = "<!-- askr:prefs-end -->"

GLOBAL_CLAUDE_MD = os.path.expanduser("~/.claude/CLAUDE.md")

_PENDING_PATH      = os.path.expanduser("~/.config/askr/behavior_pending.json")
NOTIFICATION_PATH  = os.path.expanduser("~/.config/askr/notification.json")

# Conservative on purpose: a false positive here either silently edits the
# user's CLAUDE.md with no human in the loop (headless path) or interrupts
# them with a popup for something that isn't actually a standing preference.
# A false negative just costs one more repeated instruction next session —
# that's the status quo today, so it's the safer failure mode. Set higher
# than the 0.70 bar used elsewhere (direction inference, rejected-decision
# capture) because those are read-only signals; this one writes files.
CONFIDENCE_THRESHOLD = 0.85

# Mirrors lifecycle.py's Terminal.app fallback delay (_terminal_app_fallback_worker)
# — long enough for a real IDE window to read+claim the shared notification.json,
# short enough that a genuinely headless session doesn't sit on an unpersisted
# preference for long.
FALLBACK_DELAY_SECONDS = 20


# ---------------------------------------------------------------------------
# Fenced-section read/write (CLAUDE.md, global + project)
# ---------------------------------------------------------------------------

def _project_claude_md(project_path: str = "") -> str:
    return os.path.join(project_path or os.getcwd(), "CLAUDE.md")


def _claude_md_path(scope: str, project_path: str = "") -> str:
    return GLOBAL_CLAUDE_MD if scope == "global" else _project_claude_md(project_path)


def _extract_section(content: str) -> str:
    m = re.search(
        rf"{re.escape(_PREFS_MARKER_START)}(.*?){re.escape(_PREFS_MARKER_END)}",
        content, re.DOTALL,
    )
    return m.group(1) if m else ""


def _parse_bullets(section_text: str) -> list[str]:
    bullets = []
    for line in section_text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            bullets.append(line[2:].strip())
    return bullets


def read_persisted_rules(scope: str, project_path: str = "") -> list[str]:
    """Rules already persisted in the fenced askr:prefs section for this scope.
    Fails open (empty list) on any read error — never raises."""
    path = _claude_md_path(scope, project_path)
    try:
        with open(path) as f:
            content = f.read()
    except Exception:
        return []
    return _parse_bullets(_extract_section(content))


def read_all_persisted_rules(project_path: str = "") -> dict:
    return {
        "global":  read_persisted_rules("global", project_path),
        "project": read_persisted_rules("project", project_path),
    }


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower()).rstrip(".")


def _is_similar(a: str, b: str) -> bool:
    """Conservative textual dedup: exact match after normalization, or one is
    a substring of the other (catches trivial rephrasing/truncation)."""
    na, nb = _normalize(a), _normalize(b)
    if not na or not nb:
        return False
    return na == nb or na in nb or nb in na


def _build_section(rules: list[str]) -> str:
    bullets = "\n".join(f"- {r}" for r in rules)
    return (
        f"{_PREFS_MARKER_START}\n"
        f"## Askr — Detected Preferences\n\n"
        f"Auto-detected from session conversations by askr. Edit freely — askr\n"
        f"will never overwrite content outside the fenced markers. Remove a rule\n"
        f'with `askr prefs remove "rule text"`.\n\n'
        f"{bullets}\n"
        f"{_PREFS_MARKER_END}"
    )


def write_rule(rule: str, scope: str, project_path: str = "") -> bool:
    """
    Append `rule` into the fenced askr:prefs section of the given scope's
    CLAUDE.md, creating the file/section if needed.

    Returns True if written, False if an equivalent rule was already present
    (no-op — this is what makes write_rule safe to call from both the Keep
    button path and the headless auto-persist path without double-writing).
    """
    rule = (rule or "").strip()
    if not rule:
        return False
    path = _claude_md_path(scope, project_path)

    content = ""
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()

    existing = _parse_bullets(_extract_section(content))
    if any(_is_similar(rule, e) for e in existing):
        return False

    section = _build_section(existing + [rule])

    if _PREFS_MARKER_START in content:
        content = re.sub(
            rf"{re.escape(_PREFS_MARKER_START)}.*?{re.escape(_PREFS_MARKER_END)}",
            lambda _m: section, content, flags=re.DOTALL,
        )
    else:
        content = content + (f"\n\n{section}\n" if content.strip() else f"{section}\n")

    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return True


def remove_rule(rule: str, project_path: str = "") -> str:
    """
    Search project scope, then global scope, for a matching persisted rule
    and remove it from the fenced askr:prefs section.

    Returns the scope it was removed from ("project"/"global"), or "" if not
    found in either.
    """
    for scope in ("project", "global"):
        path = _claude_md_path(scope, project_path)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            content = f.read()

        existing = _parse_bullets(_extract_section(content))
        remaining = [e for e in existing if not _is_similar(rule, e)]
        if len(remaining) == len(existing):
            continue  # not present in this scope's section

        if remaining:
            section = _build_section(remaining)
            content = re.sub(
                rf"{re.escape(_PREFS_MARKER_START)}.*?{re.escape(_PREFS_MARKER_END)}",
                lambda _m: section, content, flags=re.DOTALL,
            )
        else:
            content = re.sub(
                rf"\n*{re.escape(_PREFS_MARKER_START)}.*?{re.escape(_PREFS_MARKER_END)}\n*",
                "\n", content, flags=re.DOTALL,
            ).strip()
            content = f"{content}\n" if content else ""

        with open(path, "w") as f:
            f.write(content)
        return scope
    return ""


# ---------------------------------------------------------------------------
# Pending-candidate store — ~/.config/askr/behavior_pending.json
# Atomic write (temp file + os.replace), fail-open on read errors — same
# pattern as askr/session/model_windows.py's cache.
# ---------------------------------------------------------------------------

def _load_pending() -> list[dict]:
    try:
        with open(_PENDING_PATH) as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def _save_pending(items: list[dict]) -> None:
    try:
        os.makedirs(os.path.dirname(_PENDING_PATH), exist_ok=True)
        tmp_path = f"{_PENDING_PATH}.tmp.{os.getpid()}"
        with open(tmp_path, "w") as f:
            json.dump(items, f, indent=2)
        os.replace(tmp_path, _PENDING_PATH)
    except Exception:
        pass


def load_pending() -> list[dict]:
    return _load_pending()


def add_pending(candidates: list[dict], project_path: str = "") -> list[dict]:
    """Append new candidates to the pending store, deduped against whatever is
    already pending. Returns only the entries actually newly added."""
    from datetime import datetime, timezone

    existing = _load_pending()
    existing_rules = [p.get("rule", "") for p in existing]
    added = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for c in candidates:
        rule = (c.get("rule") or "").strip()
        if not rule or any(_is_similar(rule, e) for e in existing_rules):
            continue
        scope = c.get("scope") if c.get("scope") in ("global", "project") else "project"
        entry = {
            "rule": rule,
            "scope": scope,
            "confidence": c.get("confidence", 0),
            "project_path": project_path,
            "detected_at": now,
        }
        existing.append(entry)
        existing_rules.append(rule)
        added.append(entry)

    if added:
        _save_pending(existing)
    return added


def remove_pending(rule: str) -> bool:
    existing = _load_pending()
    remaining = [p for p in existing if not _is_similar(rule, p.get("rule", ""))]
    if len(remaining) == len(existing):
        return False
    _save_pending(remaining)
    return True


# ---------------------------------------------------------------------------
# Dedup against already-persisted / already-pending rules
# ---------------------------------------------------------------------------

def dedup_candidates(candidates: list[dict], project_path: str = "") -> list[dict]:
    """Filter out candidates that are already persisted (either scope's
    CLAUDE.md) or already sitting in the pending store — 'never re-surface an
    already-persisted rule'."""
    persisted = (
        read_persisted_rules("global", project_path)
        + read_persisted_rules("project", project_path)
    )
    pending_rules = [p.get("rule", "") for p in _load_pending()]
    known = persisted + pending_rules

    out = []
    for c in candidates:
        rule = (c.get("rule") or "").strip()
        if not rule:
            continue
        if any(_is_similar(rule, k) for k in known):
            continue
        out.append(c)
    return out


def filter_high_confidence(candidates: list[dict], threshold: float = CONFIDENCE_THRESHOLD) -> list[dict]:
    out = []
    for c in candidates:
        try:
            confidence = float(c.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0.0
        if confidence >= threshold:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Delivery — Cursor confirm popup, or headless auto-write + Discord
# ---------------------------------------------------------------------------

def deliver_candidates(candidates: list[dict], project_path: str = "", allowed_tools: list = None) -> bool:
    """
    Entry point called from checkpoint.py once high-confidence, not-yet-
    persisted behavioral preference candidates have been found for this turn.

    Adds them to the pending store first (so `askr prefs pending` sees them
    even if nothing below ever fires — e.g. this process crashes, or the
    machine sleeps before the fallback worker runs), writes notification.json
    (type=behavior_confirm) for the Cursor extension to show a Keep/Discard
    prompt, and spawns a detached fallback worker that headless-persists +
    Discord-notifies if no IDE window claims the notification within
    FALLBACK_DELAY_SECONDS.
    """
    added = add_pending(candidates, project_path)
    if not added:
        return False

    try:
        os.makedirs(os.path.dirname(NOTIFICATION_PATH), exist_ok=True)
        payload = {
            "type": "behavior_confirm",
            "message": f"Detected {len(added)} behavioral preference{'s' if len(added) > 1 else ''}",
            "rules": [
                {"rule": a["rule"], "scope": a["scope"], "confidence": a["confidence"]}
                for a in added
            ],
            "project_path": project_path,
            "allowed_tools": allowed_tools or [],
            "shown": False,
            "timestamp": added[0]["detected_at"],
        }
        with open(NOTIFICATION_PATH, "w") as f:
            json.dump(payload, f)
    except Exception:
        return False

    _spawn_fallback_worker(project_path)
    return True


def _spawn_fallback_worker(project_path: str, delay: int = None) -> None:
    """Detached subprocess: sleep, then headless-persist any candidate whose
    notification was never claimed by an IDE window. Mirrors lifecycle.py's
    _spawn_terminal_app_fallback exactly (Popen + start_new_session=True so
    it survives this process exiting)."""
    import subprocess
    import sys as _sys
    try:
        askr_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        code = (
            f"import sys; sys.path.insert(0, {askr_root!r})\n"
            f"from askr.state.behavior_prefs import _fallback_worker as w\n"
            f"w({project_path!r}, {delay!r})\n"
        )
        subprocess.Popen(
            [_sys.executable, "-c", code],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _fallback_worker(project_path: str, delay: int = None) -> None:
    """Entry point for the detached process _spawn_fallback_worker spawns."""
    import time
    time.sleep(FALLBACK_DELAY_SECONDS if delay is None else delay)
    try:
        with open(NOTIFICATION_PATH) as f:
            n = json.load(f)
        if n.get("type") != "behavior_confirm" or n.get("shown"):
            # Either a different notification has since overwritten this one,
            # or an IDE window already claimed it — Keep/Discard owns it now.
            return
    except Exception:
        return
    _headless_persist(n.get("rules", []), project_path)


def _headless_persist(rules: list[dict], project_path: str) -> list[str]:
    """Write each candidate straight into its scope's CLAUDE.md and notify
    Discord — the no-IDE-window path. Returns the rules actually persisted."""
    persisted = []
    for r in rules:
        rule = r.get("rule", "")
        scope = r.get("scope", "project")
        if write_rule(rule, scope, project_path):
            persisted.append(rule)
        remove_pending(rule)

    if persisted:
        try:
            from askr.clients.discord import send_message
            lines = "\n".join(f"- {r}" for r in persisted)
            send_message(
                f"**[askr] Detected and persisted {len(persisted)} preference"
                f"{'s' if len(persisted) > 1 else ''}:**\n{lines}\n"
                f'`askr prefs remove "..."` to undo.'
            )
        except Exception:
            pass

    return persisted
