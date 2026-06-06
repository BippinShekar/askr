Last updated: 2026-06-06 17:49

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Discord webhook integration for notifications — webhook URL validated and stored in `.env`, test message send failing, debugging HTTP response to identify root cause
- Integration test suite for all 4 checkpoint/resumption stages (7-10 tests) in CI pipeline
- End-to-end test of Stage 10 project brief generation using real checkpoint data
- Verification of test status from last Bash output and fixing any failures

## Key Decisions Made

- State persisted to git as append-only decision log, task tracking, and progress snapshots — enables full audit trail and developer handoffs
- Four-stage lifecycle: monitor token usage → forecast exhaustion → checkpoint state → resume with context injection
- Hooks integrated at session start, user prompt submit, session stop, and pre-compaction to capture context at critical moments
- Project brief auto-generated from checkpoint state to orient new developers in under 2 minutes
- Discord notifications for session events (webhook-based, async, non-blocking)

## Open Goals

- Complete Discord webhook validation debug script using urllib.