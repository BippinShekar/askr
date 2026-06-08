Last updated: 2026-06-08 19:32

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) that survives session boundaries.

## What's In Flight

- Multi-repo context-switch daemon bug fix: stale-stats check implemented in `lifecycle.py` to prevent daemon from firing handovers in the wrong repository when multiple askr projects are active. Ready for testing.
- Emergency checkpoint implementation: needs completion and verification against test suite.
- Session resumption flow: integrating checkpoint state reload with Claude Code session injection.

## Key Decisions Made

- State persisted to git, not a database. Enables offline access and natural developer workflows (commit history, diffs, blame).
- Append-only decisions log. Decisions are never edited, only appended. Preserves reasoning trail.
- Daemon monitors token usage via `session_stats.json` and JSONL session logs. Forecasts which limit (context or quota) hits first.
- Safe pause validation required before checkpoint. Prevents interrupting mid-operation.
- Session hooks injected at four points: start (context inject), prompt submit (objective capture), stop (handover commit), pre-compact