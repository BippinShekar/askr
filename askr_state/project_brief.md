Last updated: 2026-06-06 17:50

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Integration tests for all 4 stages (7-10) in CI pipeline; Stage 10 validates project brief generation end-to-end with real checkpoints.
- Discord webhook notifications: module exists and is integrated; test message successfully delivered to user's personal Discord server. Webhook URL stored in `.env` as `ASKR_DISCORD_WEBHOOK`.
- Verification of test status from last Bash output and fixing any failures.
- Review of files changed since last session and validation against decisions.md.

## Key Decisions Made

- State is append-only and persisted to git: tasks, decisions, and progress are never edited in place, only appended. This creates an audit trail and prevents merge conflicts.
- Session lifecycle is split into four stages: start (inject context), prompt submission (extract objectives), stop (generate handover docs), and pre-compact (emergency checkpoint).
- Handover documents are human-readable and include task status, failed approaches, and next steps so any developer can pick up work