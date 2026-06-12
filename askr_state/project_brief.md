Last updated: 2026-06-12 12:02

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress so work can resume without context loss.

## What's In Flight

- Validating CR/LF fix for Claude's raw-mode TUI submission (switched from LF to CR in extension handlers; committed but needs real-world trigger validation before stress test)
- Establishing overnight autonomous session switching stress test for the askr portfolio project (checklist created at `/Users/bippin/Desktop/askr/stress-tests/overnight-portfolio-tetsis.md`)
- Discord notification gating — verifying `_start_claude` boolean return properly gates notifications
- Terminal.app keystroke fallback on macOS — testing actual Claude launch behavior
- Session card display — deciding whether to show git remote or directory name in top-right

## Key Decisions Made

- State persists in git via append-only decision logs and handover documents; no external database
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion
- Extension integration via hooks at session start, prompt submit, session stop, and pre-compaction points
- Notifications routed