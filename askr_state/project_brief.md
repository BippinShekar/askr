Last updated: 2026-06-06 21:24

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and generating handover documents that let the next session resume without context loss.

## What's In Flight

- Integration test suite for all 4 stages of checkpoint/resumption pipeline (stages 7-10); currently 7-10 tests needed in CI
- End-to-end test of Stage 10 (project brief generation) using real checkpoint data
- Active session monitoring: context usage currently at 73%, daemon watching for 75%+ threshold to trigger checkpoint
- Stop hook configuration to fire checkpoint and Discord notification when session ends

## Key Decisions Made

- Append-only decision log in decisions.md; never edit existing lines, only append with timestamp and reasoning
- State persisted in git as source of truth for task/decision/progress handoff between sessions
- Four-stage pipeline: forecast exhaustion → safe pause validation → checkpoint generation → resumption with injected context
- Discord notifications trigger session handover initiation; daemon runs continuously in background
- PostToolUse stats file refreshes within 2 minutes of first tool call in new session

## Open Goals

-