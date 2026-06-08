Last updated: 2026-06-08 18:34

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It maintains developer context and task continuity across session boundaries, enabling seamless handoffs between developers and resumption of work without losing progress or context.

## What's In Flight

- Discord notification system for goal completion: stop hook generates handover docs and commits state, but notifications are not firing due to state directory resolution bug in config.py
- State directory resolution fix: get_state_dir() was reading globally stored leaps path instead of per-project path; corrected in latest commit but needs verification
- Test cycle pending: need to run goal add/completion cycle to confirm Discord notifications fire with corrected state directory

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of architectural choices
- State persisted to git as source of truth for handoffs; enables developer context recovery across sessions
- Hook-based integration with Claude Code (session_start, user_prompt_submit, stop, pre_compact) rather than direct API integration
- Forecast module predicts which limit (context or quota) exhausts first to optimize checkpoint timing
- Safe pause validation before interruption to avoid checkpointing mid-operation

## Open Goals

- Verify Discord notification fires on