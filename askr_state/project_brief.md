Last updated: 2026-06-08 23:48

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before degradation occurs. It enables seamless handoffs between developers and sessions by maintaining structured project context (tasks, decisions, progress) in version control, so any developer can resume work without losing context.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/checkpoint.py` — validates safe interruption points and persists state before context auto-compaction triggers
- Integration hooks for Claude Code lifecycle (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`) — extracting objectives and generating handover docs on session end
- State persistence layer (`askr/state/`) — reader/writer modules for loading and updating task/decision/progress files
- Token forecasting in `forecast.py` — predicting which limit (context or quota) will be hit first to trigger checkpoint at optimal time

## Key Decisions Made

- Append-only decision log in git — decisions are never edited, only appended, to maintain audit trail and prevent context loss
- State stored as structured files in git, not external databases — enables offline access, full version history, and zero infrastructure dependencies
- Checkpoint triggered before Claude's automatic context compaction,