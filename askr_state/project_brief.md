Last updated: 2026-06-06 21:42

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so work can resume without losing context.

## What's In Flight

- Auto-launch of sessions when goals are added via CLI (`cmd_goal` in askr.py) — completed and tested end-to-end.
- Daemon auto-start of sessions when idle with pending goals (`_maybe_autolaunch` in lifecycle.py) — implemented and deployed via launchctl.
- Integration tests for all 4 stages (7-10) in CI pipeline — not yet written.
- Stage 10 project brief generation end-to-end test with real checkpoint — not yet validated.
- Incomplete git commit from last session needs to be finished.

## Key Decisions Made

- State is append-only and persisted to git; decisions.md is never edited, only appended to.
- Session lifecycle is split into four stages: start (inject context), prompt (extract objectives), stop (generate handover), and pre-compact (emergency checkpoint).
- Daemon runs continuously and monitors token usage via forecast.py to predict which limit hits first.
- Handover documents