Last updated: 2026-06-09 00:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, solving the problem of losing work and context when Claude Code sessions hit their limits.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validates safe interruption points before forcing a pause
- State persistence layer (`askr/state/`) — reader/writer modules for loading and updating developer context, tasks, and decisions
- Hook integration with Claude Code — `pre_compact.py` emergency checkpoint before context auto-compaction, `stop.py` handover doc generation and git commits
- Test suite validation — verifying recent changes don't break existing functionality

## Key Decisions Made

- State stored in git as append-only decision log and mutable task/progress files — enables version control and developer handoffs without external databases
- Forecast module predicts which limit (context or quota) hits first — allows proactive checkpointing rather than reactive recovery
- Hooks injected at session lifecycle boundaries (start, prompt submit, stop, pre-compact) — minimal coupling to Claude Code internals
- Safe pause validation required before checkpoint — prevents interrupting mid-operation and corrupting