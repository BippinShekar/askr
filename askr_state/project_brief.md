Last updated: 2026-06-06 21:57

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress snapshots that Claude can resume from.

## What's In Flight

- End-to-end testing of goal functionality with Discord screenshots to verify the complete workflow
- Integration tests for all 4 stages (7-10) in the CI pipeline
- Stage 10 project brief generation end-to-end with real checkpoint data
- AppleScript string escaping fix in `askr/session/lifecycle.py` — apostrophes in goal prompts were breaking shell commands; solution is to strip apostrophes before passing to AppleScript
- Syntax validation of lifecycle.py after recent edits and daemon reload

## Key Decisions Made

- State persists to git via append-only decision logs and handover documents, enabling context recovery across sessions
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion
- Checkpoints are triggered at safe interruption points validated by `safe_pause.py` to avoid mid-operation interruption
- Claude Code integration via hooks at session start, prompt submit, session stop, and pre-compaction stages