Last updated: 2026-06-08 23:37

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, objectives, and progress in version control.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validates safe interruption points before pausing a session
- State persistence layer (`askr/state/`) — reader/writer modules for loading and updating developer context, tasks, and decisions
- Claude Code hook integration (`askr/hooks/`) — session start injection, prompt extraction, handover doc generation, and pre-compaction emergency saves
- Token forecasting in `askr/session/forecast.py` — predicts which limit (context or quota) will be hit first to trigger proactive checkpoints

## Key Decisions Made

- State is append-only in git (decisions.md, handover notes) — enables audit trail and prevents merge conflicts across developer handoffs
- Checkpoints are triggered before exhaustion, not after — safe_pause validates interruption points to avoid corrupting mid-operation work
- Handover format is structured (task, status, failed approaches, next action) — reduces context loss and ramp-up time for incoming developers
- Session lifecycle is managed