Last updated: 2026-06-06 22:32

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) that can be injected back into new Claude Code sessions, eliminating context loss and enabling long-running projects to survive session boundaries.

## What's In Flight

- Finalizing phase 3.6 completion: roadmap.md marked complete, awaiting git commit
- Stage 10 project brief generation: end-to-end test with real checkpoint data
- Verification of test suite status from last bash output and fixing any failures
- Review of files changed since last session and validation against decisions.md

## Key Decisions Made

- Append-only decision log in decisions.md: decisions are never edited, only appended, to maintain audit trail and prevent rewriting history
- State persisted in git, not external databases: enables version control, diffs, and offline handoffs between developers
- Checkpoint triggered before exhaustion, not after: safe_pause.py validates interruption points to avoid mid-operation breaks
- Modular hook architecture: Claude Code integration via session_start, user_prompt_submit, stop, and pre_compact hooks rather than monolithic integration
- Context