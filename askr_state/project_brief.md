Last updated: 2026-06-06 23:01

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or repeating effort.

## What's In Flight

- Stage 10: End-to-end testing of project brief generation from real checkpoint data. Need to verify test status from last Bash output and fix any failures.
- Session lifecycle hooks: `stop.py` generates handover docs and commits state on session end; `pre_compact.py` handles emergency checkpoint before context auto-compaction.
- State persistence layer: `reader.py` and `writer.py` manage task/decision/progress files; integration with git for durable handoffs.

## Key Decisions Made

- Append-only decision log in decisions.md—never edit existing lines, only append. Ensures audit trail and prevents accidental context loss.
- State stored in git, not external database. Keeps everything version-controlled and enables natural developer handoffs via commits.
- Forecast module predicts which limit (context or quota) hits first, allowing proactive checkpoint before either exhaustion.
- Safe pause validation before interruption—don't checkpoint mid-operation; wait