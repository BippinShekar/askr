Last updated: 2026-06-11 13:45

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Daemon self-watch and extension reload flow: Python code changes now trigger daemon restart and VS Code extension reload without manual intervention. Launchd auto-restart confirmed working. Awaiting co-founder git pull to verify end-to-end flow.
- Session card display: deciding whether to show git remote or directory name in top-right corner.
- Discord integration: generating update messages with sample session card images.
- Test verification: reviewing bash output from last session and fixing any failures.

## Key Decisions Made

- State persisted to git, not database: enables offline handoffs and full audit trail.
- Append-only decisions.md: never edit existing lines, only append. Maintains decision history.
- Daemon poll cycle: 30 seconds when session active, 60 seconds when idle. Balances responsiveness and resource usage.
- Extension as source of truth: vscode-extension/extension.js is the canonical version; installed extension syncs from it.
- Safe pause validation: interruption only happens at safe