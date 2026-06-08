Last updated: 2026-06-08 23:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before degradation occurs. It enables seamless handoffs between developers and sessions by persisting structured context (tasks, decisions, progress) so work can resume without losing momentum or repeating analysis.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validating safe interruption points before context auto-compaction triggers
- State persistence layer (`askr/state/`) — refining reader/writer modules to reliably load and update developer context across session boundaries
- Hook integration with Claude Code — ensuring `pre_compact.py` fires before context compaction and `stop.py` generates complete handover docs on session end
- Test suite validation — fixing failures identified in last session output

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of architectural choices and reasoning
- Git as source of truth for project state — all checkpoints committed with structured metadata (tasks, decisions, progress snapshots)
- Forecast module predicts which limit (context or quota) hits first to prioritize checkpoint timing
- Safe pause validation required before any interruption — prevents checkpoints mid-operation or in inconsistent states
- Handover documents auto