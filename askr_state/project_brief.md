Last updated: 2026-06-08 19:29

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent developer context, active objectives, and progress tracking in version control.

## What's In Flight

- Emergency checkpoint system: detecting safe interruption points and persisting state before context auto-compaction
- Session resumption orchestration: injecting prior context and objectives when Claude Code restarts
- Token forecasting: predicting which limit (context or quota) will be hit first to trigger checkpoints proactively
- Handover documentation: generating developer-to-developer context on session end with git commits

## Key Decisions Made

- State persisted in git (not external database) to keep project portable and version-controlled
- Append-only decision log in decisions.md to maintain audit trail without rewrites
- Safe pause validation before checkpoint to avoid interrupting mid-operation
- Hook-based integration with Claude Code (session_start, user_prompt_submit, stop, pre_compact) rather than direct API patching
- Modular architecture: session lifecycle, hooks, state layer, and QA analysis separated into distinct modules

## Open Goals

- Verify test status from last Bash output and fix any failures
- Review files