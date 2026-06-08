Last updated: 2026-06-09 00:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before degradation occurs. It enables seamless handoffs between developers and sessions by persisting structured context, decisions, and progress—solving the problem of losing work mid-task when Claude Code runs out of tokens or context window.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/checkpoint.py` — needs completion and testing
- Integration validation across hooks (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`) to ensure state flows correctly through session lifecycle
- Test suite verification — last session had failures that need diagnosis and fixes
- State file format refinement in `askr/state/` to ensure handover documents are human-readable and actionable

## Key Decisions Made

- Append-only decision log in `decisions.md` — never edit existing lines, only add new ones with timestamp and reasoning
- Git as source of truth for project state — all checkpoints commit structured context, tasks, and decisions
- Forecast module predicts which limit (context or quota) hits first to trigger checkpoint at optimal time
- Safe pause validation before interruption — `safe_pause.py` ensures Claude Code is at a logical stopping