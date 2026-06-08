Last updated: 2026-06-09 00:23

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without context loss or repetition.

## What's In Flight

- Emergency checkpoint implementation: completing the safe-pause validation logic that detects safe interruption points before context auto-compaction triggers
- State persistence layer: finalizing reader.py and writer.py to load/update developer context, tasks, and decisions across session boundaries
- Hook integration with Claude Code: wiring session_start.py, user_prompt_submit.py, and stop.py to inject context on begin and generate handover docs on end
- Test suite: verifying all modules pass unit tests after recent changes to session lifecycle and state management

## Key Decisions Made

- Append-only decision log in decisions.md: every decision is timestamped and reasoned, never edited, to maintain audit trail and prevent context drift
- Git as source of truth for state: all checkpoints, handover docs, and project context are committed to the repo so any developer can resume from the last known good state
- Forecast-first approach: predict which limit (context or quota) will be hit first so checkpoint timing