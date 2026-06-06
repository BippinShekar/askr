Last updated: 2026-06-06 22:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and generating handover documents that let anyone resume work without losing context.

## What's In Flight

- End-to-end testing of goal functionality with Discord screenshot verification to validate the core feature works in practice
- Integration tests for all 4 stages (7-10) in the CI pipeline to ensure checkpoint and resumption flows don't break
- Stage 10 project brief generation tested end-to-end with real checkpoint data
- Verification of test status from recent Bash output and fixing any failures
- Review of files changed since last session and alignment with decisions.md

## Key Decisions Made

- State is append-only and persisted to git; decisions.md is never edited, only appended to, ensuring audit trail
- Session lifecycle is split into discrete hooks (start, prompt submit, stop, pre-compact) that integrate with Claude Code without modifying its core
- Forecast module predicts which limit (context or quota) hits first to trigger checkpoint at the right moment
- Quote escaping in goal prompt injection is handled by stripping apostrophes from comment text before subprocess execution, not