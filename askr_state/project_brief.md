Last updated: 2026-06-09 00:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before degradation occurs. It solves the problem of losing work mid-task when Claude Code runs out of context or hits usage limits. The tool maintains structured developer context, objectives, and progress in git, enabling seamless handoffs between sessions and developers.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/checkpoint.py` — detecting safe interruption points and persisting state before context auto-compaction
- Integration validation across hooks layer (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`)
- Test suite verification and failure fixes from last session output
- State persistence layer refinement in `askr/state/` for task tracking and decision logging

## Key Decisions Made

- Append-only decision log in `decisions.md` — enables audit trail and prevents context loss across handoffs
- Git as source of truth for project state — all checkpoints committed with structured metadata (tasks, decisions, progress snapshots)
- Forecast module predicts which limit hits first (context vs quota) — prioritizes checkpoint trigger accordingly
- Safe pause validation before interruption — ensures Claude Code is at a stable point before checkpoint
-