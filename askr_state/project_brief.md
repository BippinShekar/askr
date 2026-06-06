Last updated: 2026-06-06 23:02

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and generating handover documents so work can resume without context loss.

## What's In Flight

- Checkpoint and project brief generation system: fully implemented, tested end-to-end (both manual and automatic "stop" trigger paths), and committed
- State persistence layer: goals, implementation state, and decisions tracked in `askr_state/` and auto-committed on checkpoint
- Session monitoring: token forecasting and safe pause validation ready for integration testing

## Key Decisions Made

- State stored in git-tracked markdown files (`askr_state/goals.md`, `askr_state/implementation_state.md`, `askr_state/decisions.md`) for human readability and version control
- Checkpoint triggered both manually (`askr checkpoint`) and automatically on session stop via Claude Code hooks
- Project brief regenerated on every checkpoint to keep orientation docs current
- Append-only decision log prevents accidental rewrites of past decisions
- Session lifecycle managed through discrete phases: start → monitor → forecast → safe pause → checkpoint → resume

## Open Goals

- Verify test status from last Bash output