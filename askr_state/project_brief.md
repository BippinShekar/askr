Last updated: 2026-06-10 11:50

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Migrating status tracking from workspace-level to per-project file paths. Updates completed in lifecycle.py, cost.py, CLI, and Cursor extension; pending verification of sed replacements in askr.py and test suite validation.
- Verifying test status from last session and fixing any failures.
- Reviewing files changed since last session against decisions.md for consistency.

## Key Decisions Made

- State persists in git as append-only decision logs and handover documents, not in ephemeral workspace metadata.
- Status tracking uses project-specific file paths (derived from workspace root hash) rather than global workspace paths, enabling multi-project isolation.
- Session lifecycle is managed by hooks into Claude Code (session_start, user_prompt_submit, stop, pre_compact) rather than polling.
- Safe interruption is validated before checkpoint to avoid corrupting mid-operation state.

## Open Goals

- Verify sed replacement in askr.py completed correctly (grep for remaining _STATS_PATH references).
- Run full test suite