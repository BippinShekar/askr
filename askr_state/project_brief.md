Last updated: 2026-06-08 23:56

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without context loss or manual state reconstruction.

## What's In Flight

- Emergency checkpoint implementation: completing the safe_pause.py validation logic and pre_compact.py hook to catch context exhaustion before Claude's auto-compaction triggers.
- State persistence layer: finalizing reader.py and writer.py to reliably load and update task/decision/progress files across session boundaries.
- Claude Code hook integration: wiring session_start.py, user_prompt_submit.py, and stop.py to inject context on begin, extract objectives on prompt, and generate handover docs on end.
- Test suite: verifying all modules pass unit tests; fixing any failures from recent changes.

## Key Decisions Made

- Append-only decision log in decisions.md: all product and architectural choices are timestamped and never edited, creating an audit trail for why the system works as it does.
- Git as source of truth for state: all checkpoints, handover docs, and project context are committed to the repo, making state portable and reviewable across developers.
-