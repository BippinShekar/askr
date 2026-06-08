Last updated: 2026-06-08 23:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/checkpoint.py` — detecting safe interruption points and persisting state before context auto-compaction
- Integration with Claude Code hooks (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`) to inject context on session begin and generate handover docs on session end
- State persistence layer (`askr/state/`) for reading/writing developer context, tasks, decisions, and progress to git-tracked files
- Token forecasting in `forecast.py` to predict which limit (context or quota) will be hit first

## Key Decisions Made

- State is append-only in git (decisions.md never edited, only appended) to maintain audit trail and enable session resumption without merge conflicts
- Checkpoints are triggered by `pre_compact.py` hook before Claude's automatic context compaction, not by daemon polling
- Handover documents are generated at session end (`stop.py`) and committed to git, making them discoverable by next