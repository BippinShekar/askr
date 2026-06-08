Last updated: 2026-06-08 19:13

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Session cost reporting: fixing `get_session_cost_summary()` to report metrics from the correct session (currently reads most recently active JSONL, causing wrong data when called after session ends). Target metrics: cache hit %, input/output tokens, total tokens, context limit % used, execution duration, files changed.
- Discord card generation for goal execution summaries (currently displays wrong session data pending cost reporting fix).
- Test status verification from last bash output and fixing any failures.

## Key Decisions Made

- State persisted to git as append-only decision log and JSONL session metrics files, enabling developer handoffs without external databases.
- Session lifecycle split into five phases: start (context injection), prompt submission (objective extraction), active monitoring (token forecasting), safe pause validation, and stop (handover doc generation and state commit).
- Cache hit % is the primary efficiency metric; "savings vs projected cost" calculations rejected as misleading.
- Thinking tokens not exposed by Claude Code API; final metrics use only available JSONL fields (input_