Last updated: 2026-06-12 20:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining a persistent, git-backed state layer that includes tasks, decisions, progress, and architectural snapshots. The core problem: Claude Code sessions degrade as context fills, and developers lose work context when sessions end. Askr prevents both by detecting exhaustion early and orchestrating safe pauses with full state recovery.

## What's In Flight

- Phase 3.10 Implementation Guard System: Multi-stage checkpoint and context-refresh mechanism to prevent session degradation. Three stages committed: (1) guard section installation in claude.md via `_install_claude_md`, (2) auto-regenerate architecture.md at checkpoint via `_regenerate_architecture_md`, (3) mid-session context refresh via `post_tool_use.py` hook.
- End-to-end verification of all three guard stages to confirm checkpoint workflow, architecture regeneration, and mid-session refresh are functioning correctly.

## Key Decisions Made

- State persisted to git, not a database. Enables code review, blame tracking, and offline handoffs.
- Checkpoint triggered by forecast, not hard limits. `forecast.py` predicts which