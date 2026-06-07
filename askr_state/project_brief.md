Last updated: 2026-06-07 08:41

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Permission inheritance system for auto-started Claude Code sessions: mapping tool grants from `.claude/settings.json` and `.claude/settings.local.json` so "always allow" persists across resumptions while "allow once" terminates with the session.
- Visual Discord reporting: generating PNG charts with matplotlib showing context savings (cost without askr vs. cost with askr), session timeline, and token burn metrics. Webhook integration via multipart file upload.
- Token burn quantification during auto-compact: analyzing terminal progress bar data to extract and display how many tokens are saved by checkpointing before context compression triggers.
- Roadmap extended through Phase 3.8 (permission continuity) with Phase 3.7 (rich visual Discord reports) committed and pushed.

## Key Decisions Made

- State persistence uses git commits with structured files (tasks, decisions, progress) in `.askr/` directory, enabling handoffs without external databases.
- Permission model distinguishes "always allow" (survives session end) from "allow once