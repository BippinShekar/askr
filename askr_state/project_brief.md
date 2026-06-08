Last updated: 2026-06-08 12:25

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Discord integration: Welcome messages tagged with developer name on askr init, verified working with shared webhook for multi-developer setups.
- Rolling context window: Last 5 Q&A exchanges now included in every ask query to improve Claude's continuity (committed to pipeline.py).
- Multi-developer state architecture: Per-developer handover and task files synced automatically at every checkpoint; co-founder and team member can share webhook while maintaining separate API keys.
- Verification pending: Test Discord welcome message implementation end-to-end and confirm tagged messages appear in shared channel.

## Key Decisions Made

- State persisted in git as append-only markdown files (handover_[name].md, current_task_[name].md, decisions.md) rather than database; enables offline access and natural diffs.
- Checkpoint triggered before context auto-compaction and on session end; safe_pause.py validates interruption points to avoid mid-operation breaks.
- Single shared Discord webhook per team with developer name tags in messages; reduces credential sprawl