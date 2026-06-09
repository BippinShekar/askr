Last updated: 2026-06-10 02:26

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Fix permission prompts in Claude Code by writing to both `allowedTools` (settings.json) and `permissions.allow` (settings.local.json) — root cause identified, dual-write implemented in stop.py and lifecycle.py, changes committed
- Verify test status from last Bash output and fix any failures
- Review files changed since last session and validate against decisions.md

## Key Decisions Made

- State persists in git, not in-memory — enables handoffs and audit trail
- Two separate config mechanisms control tool behavior: `allowedTools` controls what the model can call; `permissions.allow` controls whether permission prompts appear — both must be updated together
- Session lifecycle split into discrete hooks (start, prompt submit, stop, pre-compact) rather than monolithic monitoring — allows targeted intervention at safe points
- Forecast module predicts which limit hits first (context or quota) to trigger checkpoint before exhaustion, not after

## Open Goals

- Verify test status and fix any failures from last session
- Review all files