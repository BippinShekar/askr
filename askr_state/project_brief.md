Last updated: 2026-06-11 12:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before the session dies. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so anyone can resume work without losing context.

## What's In Flight

- Context window management: CONTEXT_TRIGGER threshold raised from 50% to 65% to prevent premature session kills during extended thinking operations. Verification and testing in progress.
- Daemon restart detection: preventing stale code execution after daemon restarts.
- Auto-continue verification: confirming the auto-continue switch fires in askr repo after daemon trigger.
- Discord integration: generating update messages with session card images.
- Test suite: verifying all tests pass after recent lifecycle.py changes.

## Key Decisions Made

- State persisted to git, not external databases. Enables offline work and natural developer handoffs.
- Checkpoint triggered before context exhaustion, not after. Prevents data loss and broken continuity.
- Auto-session-restart rejected. Askr cannot reliably preserve complete context across new sessions; manual resumption is safer.
- Extended thinking operations require higher context buffer (65% threshold). Prevents daemon from killing sessions mid-computation.
- Append-