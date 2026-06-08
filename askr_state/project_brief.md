Last updated: 2026-06-09 00:06

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that Claude can resume from.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validates safe interruption points before pausing a session
- Integration testing across session lifecycle hooks (`session_start.py`, `user_prompt_submit.py`, `stop.py`, `pre_compact.py`)
- State persistence layer (`askr/state/`) — reader/writer modules for task tracking and decision logging
- Context forecasting in `askr/session/forecast.py` — predicts which limit (context or quota) will be hit first

## Key Decisions Made

- State is append-only and stored in git; decisions.md is never edited, only appended to, ensuring full audit trail
- Handover documents are auto-generated on session end and committed alongside state files to enable context recovery
- Safe pause validation must occur before any checkpoint to prevent interrupting mid-operation
- Project context is loaded and snapshotted by `context_loader.py` to give resumed sessions full visibility into prior work

## Open Goals