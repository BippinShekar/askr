Last updated: 2026-06-08 20:12

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or repeating analysis.

## What's In Flight

- Removing accent bar visual elements from card rendering functions in `report_image.py` (session_card and morning_report_card). Changes completed; test snapshot generation in progress using python3.11.
- Emergency checkpoint implementation in `safe_pause.py` — needs completion and validation against test suite.
- Test suite verification — last run had failures; need to identify and fix blockers.

## Key Decisions Made

- State persists in git as append-only decision logs and structured state files (tasks, progress, context snapshots). This enables handoff documentation and audit trails.
- Session monitoring is forecast-driven: `forecast.py` predicts which limit (context or quota) hits first, allowing proactive checkpointing before exhaustion.
- Claude Code integration via hooks at four critical points: session start (inject context), prompt submit (extract objectives), session stop (generate handover docs), and pre-compact (emergency checkpoint).
- Python 3.11+ required for environment consistency; multiple system Python