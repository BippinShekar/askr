Last updated: 2026-06-08 22:39

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) that can be resumed without losing context.

## What's In Flight

- Emergency checkpoint implementation: completing the `safe_pause.py` validation logic to detect safe interruption points before context auto-compaction triggers
- State persistence layer: finalizing `reader.py` and `writer.py` to reliably load/save developer context, tasks, and decisions across session boundaries
- Hook integration with Claude Code: wiring `session_start.py`, `user_prompt_submit.py`, `stop.py`, and `pre_compact.py` to inject context on begin and generate handover docs on end
- Test suite: verifying all modules pass unit tests after recent changes

## Key Decisions Made

- Append-only decision log in `decisions.md` to maintain audit trail of architectural choices without rewriting history
- Git as source of truth for project state: all checkpoints committed with structured metadata for resumption
- Forecast module predicts which limit (context or quota) hits first to prioritize checkpoint timing
- Handover documents auto-generated on session end to brief next developer on