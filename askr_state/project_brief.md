Last updated: 2026-06-11 20:09

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It then orchestrates seamless session resumption by injecting saved context back into the next Claude Code session, enabling long-running development work to survive session boundaries without manual handoff friction.

## What's In Flight

- Fixing session continuation regression: commit cd774a3 broke the vscode-extension event listener that processes checkpoint notifications from the daemon. Need to restore the `type: "context"` notification handler in askr/ide/vscode-extension/extension.js.
- Deciding on UI display: whether to show git remote or directory name in session card top-right corner.
- Generating Discord update message with sample session card image for team visibility.
- Verifying test status from last bash output and fixing any failures.

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and version control of project context.
- Checkpoint triggered before context auto-compaction, not after, to preserve full state.
- Forecast module predicts which limit (context or quota) hits first to prioritize checkpoint timing.
- Safe pause validation ensures interruption only at stable points in the codebase.
- Handover documents auto-generated