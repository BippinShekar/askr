Last updated: 2026-06-12 01:53

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so any developer can resume exactly where the previous session left off.

## What's In Flight

- CR vs LF fix for Claude TUI prompt submission: lifecycle.py now returns boolean on `_start_claude()` success; both IDE handlers use sendText + CR instead of LF.
- Discord notification gating: notifications only fire when session start succeeds (awaiting verification of boolean return flow).
- Terminal.app keystroke fallback on macOS: two-step script (start Claude, then send prompt via osascript) replacing single-command approach.
- Overnight stress test scenario: placeholder created at stress-tests/overnight-portfolio-tetris.md for autonomous session switching validation.
- VSCode extension reload issue: Cursor leaps window consumed reload notification; manual reload required.

## Key Decisions Made

- State persisted to git (not database): enables offline handoffs and version history of decisions/progress.
- Boolean return from `_start_claude()` gates downstream notifications: fail-safe pattern prevents spurious alerts on launch failure.
- CR submission