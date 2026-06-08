Last updated: 2026-06-08 23:54

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so work can resume without context loss or repetition.

## What's In Flight

- Emergency checkpoint implementation: completing the `pre_compact.py` hook that triggers safe state persistence before Claude Code's automatic context compaction.
- Session resumption flow: building lifecycle logic to inject saved context and objectives when a new session starts.
- State persistence layer: refining `reader.py` and `writer.py` to reliably load and update task/decision/progress files across session boundaries.
- Test coverage: fixing failures identified in recent test runs to validate checkpoint and resumption paths.

## Key Decisions Made

- Append-only decision log in git: all product and architectural choices are recorded with timestamp and reasoning, never edited, to maintain audit trail across handoffs.
- State stored in git, not external database: enables offline work, version history, and natural integration with developer workflows.
- Hook-based integration with Claude Code: `session_start.py`, `user_prompt_submit.py`, `stop.py`, and `pre_compact.py` intercept session lifecycle