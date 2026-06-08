Last updated: 2026-06-08 22:53

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without losing context or repeating analysis.

## What's In Flight

- Emergency checkpoint implementation: completing the `safe_pause.py` validation logic to ensure interruptions happen only at safe points in the codebase
- Session resumption flow: wiring `lifecycle.py` to inject prior context and objectives when Claude Code restarts
- Hook integration with Claude Code: finalizing `pre_compact.py` to trigger checkpoints before context auto-compaction
- Test coverage: fixing failures identified in recent test runs and validating checkpoint/resume end-to-end

## Key Decisions Made

- State persisted to git, not a separate database—enables version control, diffs, and handoffs without external infrastructure
- Append-only decision log in `decisions.md`—immutable record of why choices were made, aids onboarding and prevents revisiting settled questions
- Forecast module predicts which limit (context or quota) hits first—allows proactive checkpointing rather than reactive recovery
- Hooks injected at four Claude Code lifecycle points (start, prompt submit, stop,