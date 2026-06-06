Last updated: 2026-06-06 21:34

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Integration tests for all 4 stages (7-10) of the checkpoint pipeline in CI
- End-to-end test of Stage 10 (project brief generation) with real checkpoint data
- Process kill fallback mechanism in lifecycle.py using lsof to match project working directory (recently completed and verified)
- Verification of context checkpoint mechanism working end-to-end (confirmed in last session: daemon detected 80.2% context usage, wrote checkpoint_pending.json, Stop hook consumed and committed)

## Key Decisions Made

- State persisted to git as append-only files (tasks, decisions, progress) to enable developer handoffs and session resumption
- Four-stage checkpoint pipeline: detect exhaustion → safe pause validation → state persistence → handover document generation
- Daemon monitors token usage via forecast.py to predict which limit hits first (context or quota)
- Claude Code integration via hooks at session start, prompt submit, session stop, and pre-compact events
- Process killing uses lsof fallback when standard