Last updated: 2026-06-06 22:30

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions in Cursor/VS Code, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. It then orchestrates resumption by injecting saved context back into the next session, enabling seamless handoffs between developers and long-running projects without losing work or context.

## What's In Flight

- Goal launch terminal integration: modifying `lifecycle.py` to emit `goal_launch` notifications that the Cursor extension picks up and opens integrated terminal tabs, with fallback to Terminal.app if the notification fails. Current blocker: extension not receiving notifications; premature `return` statement preventing fallback execution.
- End-to-end test of Stage 10 project brief generation with real checkpoint flow.
- Daemon reload: `com.askr.daemon.plist` was unloaded during testing and needs to be reloaded before next test run.

## Key Decisions Made

- State persisted to git, not a database: enables version control, diffs, and offline handoffs between developers.
- Append-only decision log: all decisions recorded with timestamp and reason; never edited, only appended.
- Notification-based extension communication: Cursor extension polls for notifications written by daemon rather than daemon calling extension APIs directly.
- Safe