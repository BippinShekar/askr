# Handover: bippin

Last updated: 2026-06-16 16:02

*Source of truth: `handover_bippin.json`*


## Task
Completed 7-stage goals refactoring (goals.md → goals.jsonl append-only JSONL) and identified critical workflow gaps for multi-developer task assignment and session synchronization

## Discussion
Session concluded Stage 7 with goals.jsonl migration and commit (0d68847). User then raised two critical scenarios: (1) Lochan pulling every morning to sync assigned tasks, and (2) Lochan starting a session after 4+ hours idle without pulling, risking stale task state. User is asking how askr should handle both scenarios and whether a pre-session pull hook should be implemented to prevent working in the dark on outdated assignments.

## Accomplishments
- [x] Migrated goals.md to append-only goals.jsonl with union-merge safety
- [x] Verified add_goal() and complete_goal() JSONL functions work correctly
- [x] Committed Stage 7 with .gitattributes, .gitignore, and core CLI/checkpoint updates
- [x] Pushed all changes to remote (commit 0d68847)
- [x] Identified two critical multi-dev workflow scenarios requiring pre-session sync

## Next Actions
1. Design pre-session pull hook in askr/session/checkpoint.py — implement session_start() to call git pull --rebase before any work begins, with conflict resolution strategy (abort if conflicts, notify user)
   *Why: Prevents Lochan (and any dev) from working on stale task assignments after idle periods; ensures task queue, goals, and decisions are always current*
2. Add session_start() notification to askr_state/notifications.log with timestamp and pulled commit hash; log any merge conflicts or skipped pulls
   *Why: Provides audit trail of when devs synced; helps diagnose why a dev worked on outdated tasks*
3. Document two scenarios in README or WORKFLOW.md: (A) morning pull → work all day, (B) idle 4+ hours → pre-session auto-pull. Show expected behavior for each
   *Why: Clarifies to Lochan and team what askr guarantees; sets expectations for when sync happens*
4. Implement optional --skip-pull flag for askr start (for offline work or testing); default is always pull
   *Why: Gives power users escape hatch while keeping safe default for most devs*
5. Test pre-session pull with simulated stale queue_lochan.jsonl and new task assignments from another dev; verify Lochan sees new tasks on session start
   *Why: Validates the core workflow the user is asking about; ensures no race conditions or lost updates*

## Decisions
- Pre-session pull should be mandatory by default (not opt-in) — User's concern about working 'in the dark' is a safety issue; opt-in would let devs forget and cause confusion
- Pull happens before session checkpoint is written, not after — Ensures handover JSON reflects latest remote state; prevents committing stale task references
- Merge conflicts on pull should abort the session with clear error, not auto-resolve — Conflicts indicate real divergence (e.g., two devs edited same task); requires human judgment

## Files In Play
- `askr/session/checkpoint.py`
- `askr/cli/askr.py`
- `askr_state/queue_lochan.jsonl`
- `askr_state/notifications.log`

## Relational Files
- `askr/session/checkpoint.py` (imports): Will add session_start() hook that calls git pull before checkpoint write
- `askr/cli/askr.py` (imports): CLI entry point must call session_start() when user runs askr start
- `askr_state/queue_lochan.jsonl` (configures): Pre-session pull ensures this file is always synced with remote before Lochan sees it
- `.gitattributes` (configures): Union merge strategy on JSONL files ensures pre-session pull doesn't lose task entries

## Uncommitted Files
- `askr_state/notifications.log`

## Blockers
- Need to decide: should pre-session pull be blocking (abort if fails) or warning-only (log and continue)?
