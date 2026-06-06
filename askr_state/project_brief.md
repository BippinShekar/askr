Last updated: 2026-06-06 21:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context and resuming work without manual setup.

## What's In Flight

- End-to-end testing of goal autonomy loop: verifying that goals added via CLI are picked up by the daemon on next session and injected into the launch prompt
- Integration tests for all 4 stages (7-10) in CI pipeline
- Stage 10 project brief generation end-to-end with real checkpoint data
- Daemon goal injection verification: confirming stored goals appear in session launch context

## Key Decisions Made

- State persisted in git commits at safe interruption points, not in-memory, to survive process restarts
- Checkpoint triggered by context threshold forecast, not reactive to exhaustion
- Four-stage lifecycle: monitor token usage, forecast limits, checkpoint before exhaustion, resume with injected context
- Goals stored in `~/.config/askr/session_state` and read by daemon at session start to inject into launch prompt
- Kill fallback in `lifecycle.py` passes `project_path` parameter to ensure clean resumption

## Open Goals

- Verify goal autonomy loop works end-to-end with