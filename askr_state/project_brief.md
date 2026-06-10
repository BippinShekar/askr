Last updated: 2026-06-10 17:12

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so work can resume without context loss.

## What's In Flight

- Session card reporting: displaying project name, user, timestamp, and message/exchange counts on generated session images. Changes committed; awaiting Discord update message generation.
- Daemon restart detection: preventing stale code execution when the daemon restarts mid-session.
- Auto-continue verification: confirming the auto-continue switch fires correctly in the askr repo after daemon trigger.
- Test suite validation: reviewing test status from last run and fixing any failures.

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files, enabling full handoff context between developers.
- Checkpoint triggered at safe interruption points (via `safe_pause.py`) rather than arbitrary moments, reducing risk of partial writes.
- Session lifecycle split into hooks (Claude Code integration points) and session modules (token forecasting, checkpoint logic), keeping concerns separated.
- Project context injected at session start via `session_start.py` hook, so Claude has developer history and objectives from the outset