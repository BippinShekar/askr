#!/usr/bin/env python3
"""
Reads askr_state/events.jsonl and reconstructs the session-spawn tree.

trigger_fired events carry both session_id (the session that fired) and
parent_session_id (looked up from the daemon's in-memory session_parent map
at fire time, via lifecycle._load_session_parent) — those pairs are the
tree's real edges. companion_spawned events don't know the resulting
child's session_id (it doesn't exist yet when the spawn happens) — they
carry parent_session_id only, and are attached to that parent as a
supplementary "spawned a companion here, via this trigger" marker rather
than a tree edge of their own.

A session that never fires its own trigger (finishes normally, no
context/quota/idle event) has no way to record its parent here — it simply
doesn't appear as a node. That's an accepted gap, not a bug: the story this
reconstructs is the autonomy handoff chain (which session's trigger led to
which next session), and a session that never triggered anything isn't part
of that chain.
"""

import json
import os


def load_events(state_dir: str = None) -> list:
    """
    Read every row from events.jsonl, oldest first (file is append-only, so
    file order already is chronological order — no separate sort needed).
    Malformed lines are skipped, never raised. Missing file returns [].
    """
    try:
        _dir = state_dir or os.path.join(os.getcwd(), "askr_state")
        path = os.path.join(_dir, "events.jsonl")
        if not os.path.exists(path):
            return []
        events = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
        return events
    except Exception:
        return []


def build_session_tree(events: list) -> dict:
    """
    Returns {"sessions": {session_id: node}, "roots": [session_id, ...]}.

    node = {
        "session_id": str,
        "parent_session_id": str | None,
        "project_path": str | None,
        "triggers": [event, ...],   # this session's own trigger_fired rows
        "spawns": [event, ...],     # companion_spawned rows this session caused
        "children": [session_id, ...],
    }

    roots are sessions with no known parent (parent_session_id is None, or
    names a session never itself seen with events — an orphaned reference,
    e.g. its own trigger_fired row aged out or was never captured).
    """
    sessions = {}

    def _get_or_create(session_id, project_path=None):
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "parent_session_id": None,
                "project_path": project_path,
                "triggers": [],
                "spawns": [],
                "children": [],
            }
        node = sessions[session_id]
        if project_path and not node["project_path"]:
            node["project_path"] = project_path
        return node

    # Pass 1: trigger_fired rows establish real nodes and their parent edges.
    for e in events:
        if e.get("event_type") != "trigger_fired":
            continue
        sid = e.get("session_id")
        if not sid:
            continue
        node = _get_or_create(sid, e.get("project_path"))
        node["triggers"].append(e)
        parent = e.get("parent_session_id")
        if parent and not node["parent_session_id"]:
            node["parent_session_id"] = parent

    # Pass 2: companion_spawned rows attach to their parent as activity, not
    # as a node of their own (their session_id is always None at spawn time).
    for e in events:
        if e.get("event_type") != "companion_spawned":
            continue
        parent = e.get("parent_session_id")
        if not parent:
            continue
        node = _get_or_create(parent, e.get("project_path"))
        node["spawns"].append(e)

    # Pass 3: wire children — a session_id whose parent points elsewhere
    # becomes that parent's child, but only if the parent is itself a real
    # (triggered) node; an orphaned parent reference makes this session a
    # root instead, rather than silently dropping it.
    roots = []
    for sid, node in sessions.items():
        parent = node["parent_session_id"]
        if parent and parent in sessions:
            sessions[parent]["children"].append(sid)
        else:
            roots.append(sid)

    return {"sessions": sessions, "roots": roots}
