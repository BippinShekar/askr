Last updated: 2026-06-12 12:10

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- CLI status display: fixing context/quota percentage calculations and aligning stats file lookup between CLI and VS Code extension (currently in progress by bippin).
- UTF-8 rendering in terminal: forced PYTHONIOENCODING=utf-8 to display status characters correctly; stats file path resolution now walks up directory tree to project root to match extension behavior.
- Discord notification gating: verifying _start_claude boolean return triggers notifications correctly.
- macOS Terminal.app keystroke fallback: testing Claude launch integration on actual hardware.
- Session card display: deciding whether to show git remote or directory name in top-right corner; generating sample Discord update message with session card image.

## Key Decisions Made

- State persisted to git, not external database: enables offline handoffs and full audit trail in version control.
- Append-only decision log: decisions.md never edited, only appended; enables clear history of reasoning.
- Safe pause validation before checkpoint: safe_pause.py ensures interruption happens at safe points in code execution.
- Stats