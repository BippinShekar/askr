Last updated: 2026-06-10 01:23

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so any developer can resume work without losing context.

## What's In Flight

- Permission prompt silencing: dual-write pattern implemented in stop.py and lifecycle.py to update both `allowedTools` (settings.json) and `permissions.allow` (settings.local.json). Changes staged and pushed.
- Test verification: need to confirm test status from last bash output and fix any failures.
- Session state review: verify files changed since last session and cross-check against decisions.md.

## Key Decisions Made

- State persists in git, not in-memory. Enables handoffs and audit trail.
- Token forecasting predicts which limit (context or quota) hits first, not just current usage. Allows proactive checkpointing.
- Permission silencing requires writes to both settings.json and settings.local.json. `allowedTools` controls tool availability; `permissions.allow` controls prompt suppression.
- Safe pause validation happens before checkpoint. Prevents interruption mid-operation.
- Handover docs auto-generate on session stop.