Last updated: 2026-06-06 18:40

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Phase 3.5: Guard system implementation. Async guard engine with background subprocess execution is complete. IDE popup notifications and Discord alerts are wired. Append-only audit logging to `guard_log.md` is implemented and tested.
- Integration test suite for all 4 stages (7-10) in CI pipeline. Currently verifying test status and fixing failures.
- Stage 10 project brief generation end-to-end validation with real checkpoint data.

## Key Decisions Made

- State is append-only and git-backed. All decisions, tasks, and progress are committed to version control to enable handoffs without data loss.
- Guard checks run asynchronously in background subprocesses to avoid blocking the IDE or Claude Code session.
- Notifications flow through both IDE popups (via Cursor extension) and Discord for visibility across contexts.
- Safe pause validation happens before any checkpoint to ensure interruption won't corrupt active work.
- Forecast module predicts which limit (context or quota) will be hit first to prioritize checkpoint timing.