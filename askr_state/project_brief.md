Last updated: 2026-06-12 12:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and orchestrating safe resumption without losing work or context.

## What's In Flight

- UTF-8 encoding fix for status line output: `↺` character rendering as garbled text instead of proper symbol. Staged but incomplete git commit needs completion.
- Overnight stress test validation for context recovery (CR) fix: 8-second delay before Claude TUI fully loads may be insufficient; needs real-world trigger scenario testing.
- Discord notification gating: verify _start_claude boolean return properly gates notifications.
- Terminal.app keystroke fallback on macOS: test actual Claude launch integration.
- Git remote vs directory name display decision for session card UI.

## Key Decisions Made

- State persisted to git with append-only decision log and handover documents to enable developer handoffs.
- Session lifecycle split into discrete modules: monitoring, forecasting, checkpointing, safe pause validation, and resumption orchestration.
- Claude Code integration via hooks at session start, prompt submission, session stop, and pre-compaction.
- Context recovery (CR) uses 8