Last updated: 2026-06-06 22:08

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control.

## What's In Flight

- Phase 3.6: Autonomous guard feedback loop — designing bidirectional communication from guard subprocess back into active Claude conversations to inject correction strategies, with pre/post-fix screenshots and Discord reporting
- End-to-end testing of guard functionality with Discord integration to verify goal detection and correction workflows
- Integration tests for all 4 checkpoint/resumption stages (7-10) in CI pipeline
- Stage 10 project brief generation validation with real checkpoint data

## Key Decisions Made

- Guard engine runs as detached subprocess outside active conversation (Phase 3.5 complete) — enables async Haiku cross-checks and IDE/Discord notifications without blocking Claude
- State persists in git via append-only decision logs and handover documents — enables context recovery across session boundaries and developer handoffs
- Checkpoint triggered before context auto-compaction (pre_compact hook) — prevents silent state loss during Claude's internal optimization
- Safe pause validation required before interruption — ensures checkpoints occur at stable points in execution

## Open Goals

- Run end-to-end