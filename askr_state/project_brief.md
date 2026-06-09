Last updated: 2026-06-10 03:29

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and orchestrating safe resumption.

## What's In Flight

- Fix compaction trigger logic in PreCompact and Stop hooks. PreCompact now correctly detects whether context or quota threshold was exceeded and writes trigger type to checkpoint_pending.json. Stop hook needs to read that trigger type and write appropriate restart notification (immediate for context exhaustion, deferred for quota exhaustion).
- Verify test status from last Bash output and fix any failures.
- Review files changed since last session against decisions.md for consistency.

## Key Decisions Made

- State persisted to git, not external database. Enables offline handoffs and version control of developer context.
- Checkpoint triggered by daemon monitoring, not user action. Reduces cognitive load; developers don't need to manually save state.
- PreCompact hook kills session before Claude's auto-compaction runs. Custom instructions can't prevent compaction; process termination is the only reliable escape.
- Trigger type (context vs. quota) determines restart strategy. Context exhaustion gets immediate restart notification; quota exhaustion gets deferred notification to respect