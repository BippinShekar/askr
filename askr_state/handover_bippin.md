# Handover: bippin

Last updated: 2026-06-16 17:01

*Source of truth: `handover_bippin.json`*


## Task
Implemented multi-session file locking and session registry to enable concurrent Claude Code sessions with safe shared state management across parallel developers

## Discussion
Session verified that the multi-session architecture (commit e2f7cb5) successfully landed file-level locking and session registry infrastructure. The system now tracks active Claude PIDs, implements flock-based write locks for .md files, and enables cross-session awareness via session_registry.jsonl. Handover JSON isolation per developer remains intact. Two new goals were added to track remaining work: session registry heartbeat logic and flock-based lock refinement for edge cases.

## Accomplishments
- [x] Verified multi-session file locking implementation (e2f7cb5) with flock and session registry infrastructure
- [x] Confirmed session-scoped edit cursor prevents parallel session file corruption (commit 3ef2974)
- [x] Validated multi-PID registry daemon kills all parallel sessions cleanly (commit 320e652)
- [x] Reviewed project-state handover mechanism for parallel session composition (commit 8e01e8a)

## Next Actions
1. Implement heartbeat logic in session_registry.jsonl: add last_heartbeat timestamp, stale session detection (>5min), and cleanup of dead sessions on startup
   *Why: Prevent zombie sessions from holding locks indefinitely; enable safe lock release when a Claude instance crashes*
2. Stress-test flock-based write lock under high concurrency (3+ simultaneous Claude sessions writing to goals.jsonl, decisions.jsonl, blockers.jsonl)
   *Why: Verify lock acquisition/release doesn't deadlock, timeout correctly, or lose writes under realistic team load*
3. Add lock timeout and retry logic: if flock acquisition exceeds 2s, log warning and queue write; if retry exhausted, escalate to user
   *Why: Prevent Claude from hanging indefinitely waiting for locks held by slow or stuck sessions*
4. Document multi-session concurrency model in README: explain flock strategy, session registry heartbeat, lock timeouts, and how to debug lock contention
   *Why: Clarify for users (Bippin, co-founder, Lochan) how askr handles parallel Claude sessions and what to expect*
5. Add session-aware context injection to session_start.py: load active session registry and surface 'Session X (dev_name) is working on file Y' in Claude's initial context
   *Why: Solve shared memory problem — Claude needs to know what other sessions are doing before starting work*

## Decisions
- Per-dev handover JSON files (handover_<dev>.json) are isolated by developer, not by session — Allows one developer to run multiple Claude sessions without file path collisions, but requires session registry for cross-session awareness
- JSONL append-only format is safe for concurrent writes; .md files require flock-based locking — JSONL union-merge semantics survive concurrent appends; markdown files need explicit locking or serialization
- Use flock (file-level locking) for .md and .jsonl writes rather than distributed locks or git branch conventions — flock is simple, OS-native, works across parallel processes on same machine, and avoids git merge complexity
- Session registry tracks active Claude PIDs, developer name, start time, and last heartbeat timestamp — Enables detection of stale/zombie sessions and safe lock cleanup; provides cross-session visibility

## User-Rejected Approaches
- **Restricting each developer to a single Claude Code session to avoid race conditions** — "assuming a developer using claude code is restricted to a singular session is basically being optimistic to build a underwhelming system" (domain: askr architecture / concurrency model)

## Failed Approaches
- Assuming per-dev handover JSON isolation is sufficient for multi-session safety — Handover JSONs are isolated, but shared .md files (goals.md, decisions.md, blockers.md) require explicit locking to prevent last-write-wins data loss

## Files In Play
- `askr/session/registry.py`
- `askr/hooks/session_start.py`
- `askr/hooks/post_tool_use.py`
- `askr/state/writer.py`
- `askr_state/goals.jsonl`
- `askr_state/decisions.jsonl`
- `askr_state/blockers.jsonl`
- `askr_state/session_registry.jsonl`

## Relational Files
- `askr/session/registry.py` (configures): Manages session PID tracking, heartbeat, and stale session detection
- `askr/hooks/session_start.py` (imports): Loads session registry on startup and surfaces active sessions to Claude context
- `askr/hooks/post_tool_use.py` (imports): Acquires flock before writing to shared .md and .jsonl files
- `askr/state/writer.py` (imports): Implements flock-based write lock acquisition and release for concurrent file access

## Uncommitted Files
- `askr_state/goals.jsonl`
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
