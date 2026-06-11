Last updated: 2026-06-11 13:38

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state and resuming work without manual context re-entry.

## What's In Flight

- Daemon self-reload on source code changes: lifecycle.py now watches for .py file modifications, exits cleanly, and launchd restarts with new code loaded.
- Extension reload notification: stop.py extracts handover path and sends reload_extension message to Cursor extension; extension.js displays clickable Reload button.
- Verification of auto-continue trigger in askr repo after daemon restart.
- Test status review from last Bash output and failure fixes.
- File change review since last session and decisions.md audit.

## Key Decisions Made

- State persisted to git as append-only handover documents; enables context transfer without manual copy-paste.
- Daemon lifecycle managed by launchd with KeepAlive: true; ensures daemon restarts on crash or code reload.
- Session monitoring split into forecast (predict which limit hits first) and checkpoint (persist state before exhaustion).
- Extension reload triggered by daemon notification rather than polling; reduces latency and manual intervention.
- Safe pause validation