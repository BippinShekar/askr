Last updated: 2026-06-06 22:07

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, objectives, and progress in version control. The core problem: Claude Code sessions end abruptly when limits hit, losing work and context. Askr prevents that by predicting exhaustion, pausing safely, and resuming with full state restored.

## What's In Flight

- Autonomous error correction in the guard engine: when Discord alerts fire about Claude mistakes, the system should autonomously help Claude understand proper structure, then send before/after screenshot comparisons to Discord with summaries.
- End-to-end testing of Discord alert functionality to verify guard engine goal detection works in practice.
- Integration tests for all 4 stages (7-10) in CI pipeline; Stage 10 project brief generation needs real checkpoint validation.
- Review of files changed since last session and verification against decisions.md.

## Key Decisions Made

- State persists in git via append-only decision logs and state files; developers can pick up mid-session with full context.
- Guard engine uses Haiku cross-checks on significant operations before execution; alerts route to both IDE popups and Discord async.
- Quote-stripping applied to goal prompts