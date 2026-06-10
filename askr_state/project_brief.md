Last updated: 2026-06-10 16:49

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without losing context.

## What's In Flight

- Daemon restart detection to prevent stale code execution after daemon restarts
- Verification that auto-continue switch fires correctly in the askr repo after daemon trigger
- Investigation of IDE extension installation failures and daemon status reporting issues
- Test suite validation and fixes from last session output

## Key Decisions Made

- State persisted to git as append-only decision log and structured state files (tasks, progress, context snapshots)
- Checkpoint triggered before context auto-compaction to preserve work mid-session
- Session hooks injected at four points: start (context injection), prompt submit (objective extraction), stop (handover docs), pre-compact (emergency checkpoint)
- Daemon monitors token usage and forecasts which limit (context or quota) will be hit first to trigger proactive checkpoints
- Extension status verified via filesystem checks rather than relying on IDE error messages

## Open Goals

- Add daemon restart detection to prevent stale code execution
- Verify auto-continue switch fires in askr repo after daemon trigger
- Verify test status