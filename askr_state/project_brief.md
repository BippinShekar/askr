Last updated: 2026-06-08 03:08

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Rolling window context for `ask` CLI: injecting last 5 Q&A exchanges into prompt on each invocation to replace in-memory tokenization. Implemented in `askr/qa/pipeline.py` with `_load_recent_history` function. Commit created; approach validated as viable for stateless CLI.
- Quota analysis and documentation: completed analysis showing Claude's auto-compaction burns 4-5% of quota window, takes ~4 minutes, silently drops context. Tweet draft ready.
- Test status verification: need to check bash output from last session and fix any failures.

## Key Decisions Made

- Rolling window over in-memory storage: `ask` is a stateless CLI with no persistent process between invocations, so re-embedding history on every call via rolling window is faster and simpler than maintaining in-memory tokenization.
- State persisted to git: all checkpoints, decisions, and progress tracked in append-only decision log and handover documents for visibility across sessions.
-