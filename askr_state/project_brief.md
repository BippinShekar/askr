Last updated: 2026-06-06 22:43

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so any developer can resume work without losing context.

## What's In Flight

- End-to-end testing of Stage 10 project brief generation with real checkpoint flow
- Verification of test suite status and fixing any failures from last Bash output
- Authentication diagnosis for the askr project itself (API keys, Discord bot credentials, or other systems) — last session identified environment files but needs actual error messages to proceed
- Review of files changed since last session and decisions.md alignment

## Key Decisions Made

- State persisted in git as append-only decision log and structured state files (tasks, progress, context snapshots) rather than external database
- Session monitoring split into discrete modules: token forecasting predicts which limit hits first, safe_pause validates interruption points, checkpoint persists before exhaustion
- Claude Code integration via hooks at session start, prompt submission, session end, and pre-compaction — not via direct API polling
- Handover documents generated on session stop to orient next developer without requiring state file parsing

## Open Goals

- Fix test failures and verify Stage 10