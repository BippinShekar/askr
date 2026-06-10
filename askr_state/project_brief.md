Last updated: 2026-06-10 11:40

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Fix VS Code extension status bar to display accurate context percentage for current workspace, eliminating stale data from other projects. Root cause identified: extension reads session_stats.json without validating project_path matches current workspace.
- SessionStart hook modified to write blank stats entry (ctx: 0%) immediately when session begins.
- Extension needs modification to validate session_stats.project_path against VS Code workspace root before displaying stats.
- Verify test status from last Bash output and fix any failures.

## Key Decisions Made

- State persisted in git via append-only decision log and handover documents, enabling context transfer between developers without external databases.
- Forecast module predicts which limit (context or quota) hits first to prioritize checkpoint timing.
- Safe interruption validation required before pausing to prevent mid-operation checkpoints.
- Stats file location centralized at ~/.config/askr/session_stats.json with project_path field for workspace validation.
- Hook-based integration with Claude Code (session_start, user_prompt_submit