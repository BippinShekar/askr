Last updated: 2026-06-06 17:30

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control. The core problem: Claude Code sessions end abruptly when limits hit, losing context and forcing manual recovery. Askr prevents that.

## What's In Flight

- Stage 10 completion: auto-generated project briefs via Haiku at every checkpoint (committed).
- Verification of test status from last Bash output and fixing any failures.
- Review of files changed since last session against decisions.md for consistency.

## Key Decisions Made

- Append-only decisions.md: all decisions logged with timestamp, developer, and reason; never edited retroactively. Ensures audit trail and prevents context loss.
- Two-file persistence for resumed session indicator: `~/.config/askr/resumed.json` marker written on resumption, read and cleared by `status --line` after display. Keeps state simple and CLI-friendly.
- Haiku for project brief generation: lightweight LLM call at checkpoint time to synthesize brief from current state, avoiding manual maintenance.
- Git as source of truth: all state (tasks, decisions, progress, context snapshots) committed