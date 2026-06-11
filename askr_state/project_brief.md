Last updated: 2026-06-11 21:56

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress so work can resume without context loss.

## What's In Flight

- Fix autonomous session continuation: the `claude` command must auto-submit handover prompts via stdin instead of CLI arguments. Extension changes are staged but not yet committed.
- Complete git commit for extension.js with message "fix: send prompt via stdin instead of CLI arg for auto-submission".
- Verify Cursor extension reloads after commit.
- Readiness assessment: core session monitoring and checkpointing work, but QA pipeline, snapshot modules, and several hook files are incomplete. Not ready for external users yet.

## Key Decisions Made

- State persists in git via append-only decision logs and state files, enabling developer handoffs without manual context transfer.
- Session lifecycle is managed through Claude Code hooks (session_start, user_prompt_submit, stop, pre_compact) rather than external polling.
- Forecast module predicts which limit (context or quota) will be hit first to prioritize checkpoint timing.
- Safe pause validation ensures interruption only happens at safe points in the codebase.

## Open Goals