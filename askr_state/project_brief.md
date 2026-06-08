Last updated: 2026-06-08 20:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Emergency checkpoint implementation — validating safe interruption points before context auto-compaction triggers
- Test case snapshot generation for all 6 report card scenarios (stop_auto, stop, context, quota, manual, emergency) — completed and sent to Discord for UI validation
- State persistence layer — reader/writer modules managing task/decision/progress files across session boundaries

## Key Decisions Made

- State stored in git as append-only decision logs and structured YAML files rather than database — enables code review, blame tracking, and offline access
- Checkpoint triggered before Claude Code's automatic context compaction, not after — prevents data loss during auto-recovery
- Session hooks injected at four points: start (context injection), prompt submit (objective extraction), stop (handover docs), pre-compact (emergency save) — covers all critical lifecycle transitions
- Report cards use matplotlib for visual token forecasting — accent bars removed, consistent left margins at x=0.03 for readability

## Open Goals

- Resume emergency checkpoint implementation and verify test status from last run
- Review implementation