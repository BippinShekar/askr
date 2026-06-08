Last updated: 2026-06-08 19:04

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Verification that the `get_state_dir()` fix is working end-to-end: confirming goal inference reads from the correct project state directory and handover documents are written to the right location.
- Session card generation for Phase 3.8 to display populated `completed_goals` and validate the fix is visible in system output.
- Test status review from last Bash output; fixing any failures that emerged.

## Key Decisions Made

- State is persisted in git as append-only decision logs and markdown files (goals.md, progress.md, handover.md) rather than a database, enabling version control and human readability.
- Session lifecycle is managed through hooks into Claude Code: `session_start` injects context, `user_prompt_submit` extracts objectives, `stop` generates handover and commits state, `pre_compact` emergency-checkpoints before context auto-compaction.
- Project path resolution is centralized in `askr/state/config.py` via `get_state_dir()`