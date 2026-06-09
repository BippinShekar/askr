Last updated: 2026-06-10 00:36

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- End-to-end testing of notification flow: verifying that Cursor extension correctly receives daemon notifications and launches terminals with the correct project path (cwd parameter).
- Commit d384faf merged: wired `project_path` and `allowed_tools` through both notification paths (Stop hook and daemon fallback).
- Extension notification handling verified in code; next step is live testing in Cursor.

## Key Decisions Made

- State persisted to git (not database) to enable offline handoffs and version history of decisions/progress.
- Checkpoint triggered before context auto-compaction (pre_compact hook) to prevent data loss during Claude's internal cleanup.
- Notification flow split into two paths: Stop hook (immediate, during session) and daemon fallback (asynchronous, if session crashes).
- Project path and allowed tools passed through notification.json so extension can launch terminals in correct directory.

## Open Goals

- Test goal launch notification in Cursor: trigger a goal and verify terminal opens with correct working directory.
- Verify test