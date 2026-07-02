# Handover: bippin

Last updated: 2026-07-02 13:05

*Source of truth: `handover_bippin.json`*


## Task
Deduped 14 repeated voice notification decisions from decisions.jsonl, confirmed session quota/context-cut warning infrastructure exists in lifecycle.py and monitor.py, and rescoped Stage 4 of voice feature to add real session limit quota warning messages (distinct from existing context-persistence notifications).

## Discussion
Prior sessions had scoped voice notifications into 3 stages and committed config scaffolding. This session discovered that Stage 4 (user-facing warnings) must distinguish between two existing notification types: (1) quota trigger at 90% (already fires via QUOTA_TRIGGER in lifecycle.py:1234-1236, writes to Discord/notification.py), and (2) context-cut persistence messages (fired when session switches to prevent compaction). User requested building real session limit quota warning messages from scratch, separate from these existing triggers. Session also cleaned up 14 duplicate decision entries in decisions.jsonl that had accumulated across prior checkpoints.

## Accomplishments
- [x] Removed 14 repeated voice notification decision entries from askr_state/decisions.jsonl (kept original 3: macOS-only/say, additional-sink-not-separate-system, machine-level config storage)
- [x] Verified existing quota trigger infrastructure: QUOTA_TRIGGER=90.0 in askr/session/lifecycle.py:1234-1236 fires when API quota hits 90%, writes notification and Discord message
- [x] Confirmed context-cut persistence messages exist as separate notification type (fired on session context switch to prevent compaction, distinct from quota warnings)
- [x] Identified that Stage 4 voice feature must add NEW real session limit quota warning messages, not reuse existing quota/context-cut infrastructure

## In Progress
- `None`: Rescoping Stage 4 of voice notification feature to clarify what 'session limit quota warning messages' means and how they differ from existing quota_pct trigger and context-persistence notifications

## Next Actions
1. Clarify with user: what constitutes a 'real session limit quota warning message' — is this a new trigger threshold (e.g. 75% quota), a different message format, or integration with a new quota tracking mechanism not yet in lifecycle.py?
   *Why: Session ended mid-rescope; existing quota_pct trigger at 90% already exists and fires notifications, so Stage 4 scope is ambiguous without user clarification*
2. Once Stage 4 scope is clarified, update next_actions to include implementation steps for new quota warning infrastructure (likely in askr/session/lifecycle.py or askr/session/monitor.py)
   *Why: Cannot proceed with implementation until Stage 4 requirements are concrete*
3. Commit askr_state/decisions.jsonl deduplication (14 lines removed, file now 407 lines)
   *Why: Cleanup is complete and ready; reduces noise in future decision history*

## Decisions
- Voice notifications use native macOS `say` command directly, not a cross-platform TTS abstraction — Project is macOS-only; `say` is built-in and reliable; no cross-platform users to support
- Voice client follows Discord client pattern: silent failure if `say` unavailable, guarded by load_voice_enabled() — Consistent error handling; non-blocking; matches existing notification sink design
- Voice notification preference stored as machine-level boolean in global ~/.config/askr/config.json, not per-project — Voice is a user/machine trait (do I want this Mac to talk), not a per-project secret like discord_webhook; mirrors developer name pattern in config.py
- Voice notifications integrate as additional sink in existing notification infrastructure (askr/hooks/stop.py, notification.py) rather than separate system — Minimizes mechanical changes; reuses existing hook patterns and state management for Discord notifications
- get_state_dir() must always return current project's state directory without fallback to other projects' stored paths — Cross-project path contamination is a critical security issue; each project must maintain isolation
- Nested worktree cwd-drift lockout left unfixed pending recurrence outside collision scenarios — Bug is genuine but rare; fixing requires deeper refactor of worktree state tracking; defer until it recurs in non-collision context

## Files In Play
- `askr_state/decisions.jsonl`
- `askr/session/lifecycle.py`
- `askr/session/monitor.py`
- `askr/hooks/notification.py`
- `askr/hooks/stop.py`

## Relational Files
- `askr/clients/discord.py` (imported_by): Voice client will follow same pattern (sink with error guard)
- `askr/state/config.py` (configures): Contains load_voice_enabled() and save_voice_enabled() scaffolding from prior session
- `askr/cli/askr.py` (imports): Will contain Stage 3 init-time prompt for voice enable/disable (around line 740-750)

## Uncommitted Files
- `askr_state/decisions.jsonl`
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Stage 4 scope ambiguity: user requested 'real session limit quota warning messages from scratch' but existing QUOTA_TRIGGER at 90% already fires quota notifications; unclear what new messages Stage 4 should add
