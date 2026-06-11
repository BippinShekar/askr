Last updated: 2026-06-11 13:41

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress so work can resume without losing context.

## What's In Flight

- Daemon auto-reload on Python file changes: file-watch loop in lifecycle.py detects `.py` modifications and triggers clean exit; launchd restarts daemon with new code. VSCode extension now has manual Reload button in status bar.
- End-to-end verification of daemon reload cycle pending: need to make test change and confirm daemon picks it up within 30-60 seconds.
- Discord integration: generate update message with sample session card image.
- Stale code execution prevention: add daemon restart detection to session loop.

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files; enables full handoff context between developers.
- Daemon monitors token usage and forecasts which limit (context or quota) hits first; checkpoints before exhaustion, not after.
- Safe interruption validated before pause: `safe_pause.py` ensures no mid-operation checkpoint.
- VSCode extension synced from source at `askr/ide/vscode-extension/extension