Last updated: 2026-06-06 18:06

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context window or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and generating handover documents that let anyone resume work without context loss.

## What's In Flight

- Integration test suite for all 4 stages (stages 7-10) in CI pipeline — currently in progress, needs completion and verification
- End-to-end test of Stage 10 (project brief generation) using real checkpoint data
- Secrets scrubbing fix: environment details (Discord webhook URL) were leaked in a recent commit and need to be reverted; secrets scrubbing function is implemented in checkpoint.py but the leaked commit must be removed from history
- README.md updates for Discord setup and askr report command documentation

## Key Decisions Made

- State is append-only and stored in git; decisions.md is never edited, only appended to, ensuring full audit trail
- Session lifecycle is split into discrete modules: monitoring (token forecasting), checkpointing (safe pause validation), and resumption (context injection)
- Claude Code integration happens via hooks at four points: session start, user prompt submission, session stop, and pre-compaction
- Handover documents