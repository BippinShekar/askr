Last updated: 2026-06-08 19:38

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so anyone can pick up where the last person left off.

## What's In Flight

- Emergency checkpoint implementation: completing the safe-pause validation logic that prevents interruption at unsafe points in code execution
- Output token calculation fix: scoped per-session instead of scanning entire JSONL (completed by bippin, pending verification)
- Snapshot report UI cleanup: removed vertical color accent bars from report cards (completed by bippin, pending test verification)
- Test suite validation: verifying all tests pass after recent changes to monitor.py, post_tool_use.py, cost.py, and report_image.py

## Key Decisions Made

- State persists in git as append-only decision logs and structured JSON files (tasks, progress, context snapshots) so handoffs are explicit and auditable
- Token forecasting predicts which limit hits first (context vs quota) to trigger checkpoints before exhaustion, not after
- Session stats written to session_stats.json at runtime to avoid re-scanning entire JSONL history when calculating costs
- Hooks integrate at four Claude Code lifecycle points: session start