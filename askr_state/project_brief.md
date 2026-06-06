Last updated: 2026-06-06 17:57

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Cost tracking and display for API usage (Haiku pricing per request). Currently designing where to capture costs, how to aggregate per session/user, and best UI location for display.
- Integration tests for all 4 checkpoint/resumption stages (7-10) in CI pipeline. Stage 10 (project brief generation end-to-end) needs real checkpoint validation.
- Verification of test status from last run and fixing any failures.
- Review of files changed since last session and decisions log.

## Key Decisions Made

- State persists in git via append-only decision logs, task files, and handover documents. This enables context recovery across developer switches and session restarts.
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion.
- Stop and PreCompact hooks default to 60-second timeouts (higher than other hooks) to allow safe state persistence before Claude Code interrupts.
- Handover documents are generated on session end and committed without Claude as co-author