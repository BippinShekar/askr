# Handover: bippin

Last updated: 2026-06-15 15:27

*Source of truth: `handover_bippin.json`*


## Task
Diagnose and fix the architectural gap where autonomous session handovers lack directive continuity — next_actions are inferred from transcript/git but don't drive actual work, making askr unsuitable for cross-team adoption.

## Discussion
The session exposed a critical flaw: handover.md generates next_actions by analyzing past work (transcript + git diff), but this is reactive inference, not proactive direction. An autonomous session reads it and has no guarantee the inferred actions align with what the user actually wants next. The team discussed three paths: (1) explicit per-session task queues (defeats adoption — users won't maintain them), (2) roadmap-driven inference (only works if roadmap is actively maintained, which most teams don't do), (3) a hybrid task queue system where any team member can append directives to another dev's queue, drained at session start. Option 3 emerged as the only path that scales without requiring user discipline, but it requires Phase 5 (approval gates) first to prevent privilege escalation.

## Accomplishments
- [x] Identified root cause: next_actions are inferred post-hoc from git/transcript, not derived from explicit user intent
- [x] Mapped three potential solutions and rejected two (explicit queues, roadmap-only) as adoption blockers
- [x] Designed Phase 4-1 (task queue per developer) as the viable path forward
- [x] Restructured roadmap.md to move Phase 4 from 'Public Launch' to 'Team Scale' with concrete queue architecture

## Next Actions
1. Design and document the approval gate system (Phase 5) — define what permissions a queued task from another developer should inherit, and how to surface them for approval before session start
   *Why: Phase 4-1 (task queue) is unsafe without this; a developer could queue a dangerous operation under another dev's session context*
2. Implement Phase 4-0 (team directory structure) — refactor askr_state/ to use teams/<team>/members/<dev>/ layout and update reader/writer to resolve paths via team config
   *Why: Prerequisite for task queue and all concurrent team features; current flat layout breaks at scale*
3. Implement Phase 4-1 stage 1 — add `askr task queue <dev> "..."` CLI command that appends to tasks/queue.md with author + timestamp
   *Why: Enables cross-developer task assignment; unblocks the core adoption problem (directive continuity without user discipline)*
4. Update session_start.py to drain queue.md at session begin, inject queued tasks into LLM context before first prompt, archive drained tasks to queue_done.md
   *Why: Makes queued tasks actually drive the session; closes the loop between 'task assigned' and 'session executes it'*
5. Stress-test Phase 4-1 with 2–3 developers queuing tasks to each other across 5+ sessions; verify no git conflicts, no lost tasks, correct execution order
   *Why: Validates the team-scale architecture before moving to Phase 4-2 (team CLI) and Phase 4-3 (concurrency)*

## Decisions
- Rejected explicit per-session task queues as the primary solution — Requires users to manually maintain task lists per session — adds friction, kills adoption. Only viable as a fallback for power users.
- Rejected roadmap-only inference as sufficient — Most teams don't actively maintain roadmaps; relying on it means askr becomes useless the moment the roadmap goes stale.
- Chose git-native append-only task queue (Phase 4-1) as the core solution — No new infrastructure, no server, no real-time connection required. Any team member can queue work. Audit trail built-in. Scales to team size without discipline.
- Moved Phase 4 from 'Public Launch' to 'Team Scale' in roadmap — Public launch is premature without team features. The product is not useful for cross-team adoption until task queues work. Team scale is the blocker.

## User-Rejected Approaches
- **Building Phase 3.12 (rejection tracking) would help solve the handover directive continuity problem** — "Brutally honest: 3.12 doesn't fix this problem at all. It's a separate concern." (domain: architecture/roadmap prioritization)

## Failed Approaches
- Inferring next_actions purely from git diff + transcript analysis — Reactive, not proactive. An autonomous session has no guarantee the inferred actions match user intent. Leads to token waste re-verifying the same work.
- Relying on users to maintain explicit task queues per session — Adds friction, requires discipline, kills adoption. Only works for power users.
- Roadmap-driven inference as the primary continuity mechanism — Assumes roadmaps are actively maintained. Most teams don't; the system becomes useless when roadmap goes stale.

## Files In Play
- `roadmap.md`

## Relational Files
- `askr/session/checkpoint.py` (configures): Generates next_actions via LLM; needs to be updated to accept queued tasks as input
- `askr/session/session_start.py` (configures): Entry point for sessions; must drain task queue and inject into context before first prompt
- `askr/state/reader.py` (configures): Must be updated to resolve team-scoped paths (Phase 4-0)
- `askr/state/writer.py` (configures): Must be updated to write to team-scoped paths and handle queue archival

## Uncommitted Files
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Phase 5 (approval gates) must be designed before Phase 4-1 ships — task queues are unsafe without permission boundaries
