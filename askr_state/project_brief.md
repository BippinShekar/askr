Last updated: 2026-06-06 22:18

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress so work can resume without losing context.

## What's In Flight

- Terminal integration: switching goal launch from AppleScript (Terminal.app) to VS Code/Cursor integrated terminal via extension notification system. Extension handler exists; lifecycle.py needs to write notification file instead of spawning osascript.
- Stage 10: end-to-end test of project brief generation with real checkpoint. Verify test status from last bash output and fix failures.
- Handover review: check files changed since last session and validate decisions.md is current.

## Key Decisions Made

- State persisted to git, not database. Enables version control, diffs, and handoffs without external infrastructure.
- Append-only decisions log. Never edit existing lines; new decisions appended with timestamp and reason. Maintains audit trail.
- Checkpoint triggered before exhaustion, not after. Safe pause validation ensures interruption happens at stable points (end of function, test pass).
- Extension notification system for terminal launch, not AppleScript. Keeps askr in VS Code/Cursor context instead of spawning separate Terminal.app