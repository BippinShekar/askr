Last updated: 2026-06-06 22:24

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that survive session interruptions.

## What's In Flight

- Guard rail system for pre/post tool use hooks: retry tracking, escape hatch escalation on repeated blocks, and resolution detection when previously-blocked files succeed. All 4 stages implemented and committed.
- End-to-end testing of Stage 10 project brief generation with real checkpoint flow.
- Verification of test suite status and fixing any failures from last session.

## Key Decisions Made

- State persists in git as append-only decision logs and structured state files (tasks, progress, context snapshots) rather than in-memory or external databases. Enables offline handoffs and full audit trail.
- Checkpoint triggered by forecast module predicting exhaustion, not reactive to hard limits. Allows graceful pause before Claude Code auto-compacts context.
- Guard blocks tracked per-file in `guard_blocks.json` with cooldown bypass on repeat offenders. Escape hatch (allow + Discord alert) fires at 2 blocks per file to unblock developer while escalating to human review.
- Session hooks (