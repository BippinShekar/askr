Last updated: 2026-06-12 16:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Stats file path synchronization: consolidating multiple modules writing to different filenames (`leaps-backend.json` vs `leaps.json`) via shared `get_project_root()` utility. Changes staged, awaiting commit.
- Discord notification gating: verifying that `_start_claude` boolean return properly gates notifications.
- macOS Terminal.app keystroke fallback: testing actual Claude launch integration.
- Session card UI: deciding on display format (git remote vs directory name) and generating sample Discord update message with card image.
- Test suite validation: verifying all tests pass after recent changes.

## Key Decisions Made

- Session state persists in git via append-only decision log and handover documents, enabling context transfer between developers.
- Project root detection centralized in shared utility to prevent path sync bugs across extension, CLI, and stats writer.
- Checkpoint triggered before context auto-compaction to prevent data loss during Claude's internal cleanup.
- Forecast module predicts which limit (context or quota) hits