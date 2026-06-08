Last updated: 2026-06-09 00:16

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent developer context, active objectives, and progress tracking. The core problem: Claude Code sessions end abruptly when limits hit, losing context and forcing manual recovery. Askr prevents that.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validates safe interruption points before state persistence
- Integration hooks across Claude Code lifecycle: session start (context injection), user prompt submit (objective extraction), session stop (handover doc generation), pre-compact (emergency checkpoint)
- State persistence layer (`askr/state/`) — reader/writer modules for tasks, decisions, and progress tracking
- Token forecasting in `forecast.py` — predicts which limit (context or quota) will be hit first to trigger checkpoint at optimal time

## Key Decisions Made

- State stored in git as append-only decision log and structured state files, not external database — enables version control and offline handoffs
- Checkpoint triggered before Claude's automatic context compaction, not after — prevents loss of critical context during auto-compaction
- Session lifecycle managed through hooks rather than direct Claude Code API — reduces coupling and allows