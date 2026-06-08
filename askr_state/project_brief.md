Last updated: 2026-06-09 00:08

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without context loss or repetition.

## What's In Flight

- Emergency checkpoint implementation: completing the `safe_pause.py` validation logic to ensure interruptions only happen at safe points in the codebase
- Session resumption flow: wiring `lifecycle.py` to inject prior context and objectives when a new session starts
- State persistence layer: finalizing `reader.py` and `writer.py` to reliably load/save developer context, tasks, and decisions across session boundaries
- Hook integration with Claude Code: testing `session_start.py`, `user_prompt_submit.py`, `stop.py`, and `pre_compact.py` to ensure they fire at the right lifecycle moments

## Key Decisions Made

- State stored in git as append-only decision logs and structured YAML files, not a database—enables version control and offline handoffs
- Forecast module predicts which limit (context or quota) hits first, prioritizing the constraint that matters most for that session
- Safe pause validation required before checkpoint—never interrupt mid-refactor or during