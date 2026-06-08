Last updated: 2026-06-08 19:09

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task/decision/progress context that Claude can resume from.

## What's In Flight

- Fixing session cost/metrics reporting: `get_session_cost_summary()` currently reads the wrong JSONL file during multi-session testing, causing cross-contamination of token/cost data. Need to bind metrics to specific goal execution data instead of most-recently-active file.
- Implementing goal-specific metrics snapshot: session token consumption (input/output split), context % used, execution duration, thinking vs output token ratio.
- Verifying test status from last bash output and fixing any failures.

## Key Decisions Made

- State persists in git as append-only decision log, task files, and progress snapshots — enables full context recovery across sessions and developers.
- Session monitoring happens via hooks into Claude Code lifecycle (start, prompt submit, stop, pre-compact) rather than external polling.
- Forecast module predicts which limit hits first (context vs quota) to trigger checkpoint at optimal time.
- Cost/metrics are goal-scoped, not session-scoped — prevents metrics pollution when multiple sessions run in parallel.

##