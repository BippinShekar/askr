Last updated: 2026-06-12 11:55

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and across sessions by maintaining a persistent state layer (tasks, decisions, progress) and orchestrating safe resumption with full context injection.

## What's In Flight

- Validating CR vs LF fix for Claude's raw-mode TUI submission (lifecycle.py and vscode-extension.js modified; changes committed but not yet tested in live session).
- Establishing overnight stress test scenario for autonomous session switching with full checklist at `stress-tests/overnight-portfolio-tetris.md`.
- Discord notification gating: verifying `_start_claude` boolean return properly gates notifications before session launch.
- Terminal.app keystroke fallback on macOS: testing actual Claude launch with two-step script (start claude, then send prompt via osascript).
- Deciding whether to display git remote or directory name in Discord card top-right.

## Key Decisions Made

- State is append-only and persisted to git; decisions.md is never edited, only appended (audit trail).
- Session lifecycle splits into five stages: monitor (token tracking), forecast (predict which limit hits first), checkpoint (persist before exhaustion), safe_pause