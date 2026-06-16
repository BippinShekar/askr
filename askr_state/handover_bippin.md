# Handover: bippin

Last updated: 2026-06-16 16:41

*Source of truth: `handover_bippin.json`*


## Task
Identified critical multi-session race condition vulnerability in concurrent Claude Code usage and surfaced architectural gap in shared state management across parallel sessions

## Discussion
Session exposed that Bippin and co-founder running multiple Claude Code sessions simultaneously creates unsolved race conditions on shared files (especially .md outputs). While JSONL append-only and per-dev handover JSONs are safe, the system lacks cross-session memory coherence and conflict resolution for concurrent writes. User rejected the assumption that restricting to single sessions per developer is acceptable — the real product must handle parallel Claude sessions as a first-class use case, not an edge case.

## Accomplishments
- [x] Surfaced git pull failure warnings in session_start.py to prevent stale work
- [x] Identified that concurrent Claude sessions create race conditions on shared markdown outputs
- [x] Recognized that per-dev handover JSON isolation works, but cross-session memory coherence is missing

## Next Actions
1. Design multi-session lock/lease mechanism for shared file writes (e.g., flock on .md files, or distributed lock via git branch naming convention)
   *Why: Prevent simultaneous writes to goals.md, decisions.md, blockers.md from different Claude sessions; last-write-wins is data loss*
2. Implement session registry (session_registry.jsonl) that tracks active Claude PIDs, session owner, start time, and last heartbeat
   *Why: Enable cross-session awareness so one Claude instance can detect and respect concurrent work by other sessions*
3. Build conflict resolution strategy for .md files: either merge-on-read (union semantics like JSONL) or queue writes and serialize via git
   *Why: Ensure that Bippin + co-founder + Lochan running 3+ sessions in parallel don't lose each other's updates*
4. Add session-aware context injection: when Claude starts, load not just own handover but also active session registry to surface what other Claude instances are doing
   *Why: Solve the shared memory problem — Claude needs to know 'Session 2 (co-founder) is refactoring auth.py right now' before it starts work*
5. Document the multi-session architecture decision and update README with concurrency model
   *Why: Clarify that askr is designed for teams with multiple concurrent Claude Code sessions, not single-session-per-dev*

## Decisions
- Per-dev handover JSON files (handover_<dev>.json) are isolated by developer, not by session — Allows one developer to run multiple Claude sessions without file path collisions, but requires session registry for cross-session awareness
- JSONL append-only format is safe for concurrent writes; .md files are not — JSONL union-merge semantics survive concurrent appends; markdown files need explicit locking or serialization

## User-Rejected Approaches
- **Restricting each developer to a single Claude Code session to avoid race conditions** — "assuming a developer using claude code is restricted to a singular session is basically being optimistic to build a underwhelming system" (domain: askr architecture / concurrency model)

## Failed Approaches
- Assuming per-dev handover JSON isolation is sufficient for multi-session safety — Handover JSONs are isolated, but shared .md files (goals.md, decisions.md, blockers.md) still have race conditions when multiple Claude sessions write simultaneously

## Files In Play
- `askr/hooks/session_start.py`
- `askr_state/notifications.log`
- `goals.jsonl`
- `decisions.jsonl`
- `queue_*.jsonl`
- `handover_*.json`

## Relational Files
- `askr/hooks/session_start.py` (configures): Entry point for session initialization; where git pull and stale-work detection happen
- `goals.md` (imported_by): Shared file written by multiple concurrent Claude sessions; needs locking or merge strategy
- `decisions.md` (imported_by): Shared file written by multiple concurrent Claude sessions; needs locking or merge strategy
- `blockers.md` (imported_by): Shared file written by multiple concurrent Claude sessions; needs locking or merge strategy

## Uncommitted Files
- `askr_state/notifications.log`

## Blockers
- Multi-session race condition on shared .md files (goals.md, decisions.md, blockers.md) — no locking or conflict resolution strategy yet
- Cross-session memory coherence missing — one Claude session has no awareness of what other concurrent sessions are doing
