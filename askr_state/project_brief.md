Last updated: 2026-06-06 17:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context. The core problem: Claude Code sessions have hard limits, and hitting them mid-task loses work and breaks momentum.

## What's In Flight

- Discord server bot integration for multi-user session notifications. All 10 implementation stages completed and pushed to main (commits b60a8ca through latest). Notifications fire on every checkpoint type; resumed sessions display a status line via ~/.config/askr/resumed.json.
- Critical blocker: per-user session isolation model for Discord deployment. Current design shares session state across all server users—need to determine if sessions are keyed by Discord user ID and how to isolate state per user.
- Integration test suite for all 4 checkpoint stages (7-10) in CI pipeline. Stage 10 (project_brief.md generation by Haiku at every checkpoint) needs end-to-end validation with real checkpoints.

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files. Enables full audit trail and offline handoffs.
- Checkpoint triggered before context