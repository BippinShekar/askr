Last updated: 2026-06-10 02:30

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so work can resume without manual context reconstruction.

## What's In Flight

- Verifying test status from last session and fixing any failures
- Reviewing files changed since last session against decisions.md to catch any drift
- Evaluating whether askr should implement automatic behavior persistence (research completed; decision pending on whether to add project-specific behavior rules layer on top of global CLAUDE.md)

## Key Decisions Made

- Session state persists in git via `askr/state/` (reader/writer modules), not in memory or daemon state. This makes state portable and auditable.
- Hooks integrate at Claude Code boundaries (session start, user prompt submit, session stop, pre-compact) rather than patching Claude itself. Keeps askr decoupled and maintainable.
- Global user behavior patterns belong in `~/.claude/CLAUDE.md` (Claude's native mechanism), not in askr. Askr may add project-specific behavior rules as a future layer, but won't duplicate global persistence.
- Forecast module predicts which limit (context or quota)