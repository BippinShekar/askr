Last updated: 2026-06-08 23:38

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/checkpoint.py` — detecting safe interruption points and persisting state before context auto-compaction triggers
- Integration validation across all hooks (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`) to ensure state flows correctly through session lifecycle
- Test suite fixes — verifying all unit tests pass after recent changes to state writer and context loader
- Handover document generation in `stop.py` — ensuring outgoing developer context is complete and actionable for next session

## Key Decisions Made

- State persisted as append-only git commits, not database — enables full audit trail and works offline
- Forecast module predicts which limit (context or quota) hits first — allows proactive checkpoint before either exhausts
- Safe pause validation required before any checkpoint — prevents interrupting mid-transaction or during critical operations
- Hook injection at Claude Code boundaries (start, prompt submit, stop, pre-compact) — minimal coupling, maximum observability