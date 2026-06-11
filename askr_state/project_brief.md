Last updated: 2026-06-11 22:43

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Session lifecycle orchestration: monitoring token usage, forecasting which limit hits first, triggering safe checkpoints before exhaustion, and resuming with full context injected
- Claude Code extension integration: hooks at session start, prompt submission, session end, and pre-compaction to extract objectives and persist state
- Terminal.app fallback keystroke delivery for prompt submission when direct Claude APIs unavailable
- Discord notifications on session resumption with session card metadata

## Key Decisions Made

- State persists in git as append-only decision logs and task files, enabling full audit trail and developer handoffs
- Line ending protocol: CR (carriage return) required for prompt submission in Claude's raw-mode TUI, not LF
- Session resumption gated on successful Claude launch confirmation (boolean return from _start_claude)
- Extension reload triggered via Python script to notify Cursor of code updates without manual restart

## Open Goals

- Decide: display git remote or directory name in session card top-right
- Generate Discord update message with sample session card image