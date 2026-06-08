Last updated: 2026-06-08 22:48

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validates safe interruption points before pausing a session
- State persistence layer (`askr/state/`) — reader/writer modules for loading and updating task context, decisions, and progress
- Claude Code hook integration (`askr/hooks/`) — session start injection, prompt extraction, and handover document generation on session end
- Token forecasting in `askr/session/forecast.py` — predicts which limit (context or quota) will be hit first to trigger checkpoint at optimal time

## Key Decisions Made

- State stored in git as append-only decision log and structured state files (tasks, progress, context snapshots) — enables full audit trail and seamless developer handoffs
- Checkpoint triggered before exhaustion, not after — prevents loss of work and maintains clean resumption point
- Hook-based integration with Claude Code rather than direct API patching — reduces maintenance surface and keeps Askr decoupled from Claude internals
- Safe pause validation required before