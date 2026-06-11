Last updated: 2026-06-11 22:32

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control.

## What's In Flight

- Emergency checkpoint system: detecting safe interruption points and persisting state before context auto-compaction
- Session resumption flow: injecting prior context and objectives when Claude Code restarts
- Handover documentation: generating developer-to-developer context cards with session summary, blockers, and next steps
- Discord integration: creating visual session cards for team updates
- Test suite validation: verifying all recent changes pass CI

## Key Decisions Made

- State persists in git, not external databases, so handoffs work across any environment and are auditable
- Checkpointing happens automatically before exhaustion, not reactively after failure
- Session hooks (start, prompt submit, stop, pre-compact) are the integration layer with Claude Code; no direct API dependency
- Context forecasting predicts which limit (context or quota) hits first to prioritize checkpoint timing
- Safe pause validation ensures interruption only happens at stable project states, not mid-operation

## Open Goals

- Decide whether to display git remote or directory name in handover card header
-