Last updated: 2026-06-09 00:22

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Emergency checkpoint implementation in `askr/session/safe_pause.py` — validating safe interruption points before state persistence
- Integration testing across session lifecycle hooks (start, prompt submit, stop, pre-compact)
- Handover document generation and git commit automation on session end
- State reader/writer refinement for task and decision persistence

## Key Decisions Made

- State persisted to git as source of truth for developer context and project continuity
- Append-only decision log in decisions.md to maintain audit trail without rewrites
- Forecast module predicts which limit (context or quota) hits first to trigger checkpoint at optimal time
- Safe pause validation required before any checkpoint to prevent mid-operation interruption
- Claude Code integration via hooks rather than direct API to respect session boundaries

## Open Goals

- Complete emergency checkpoint implementation and verify safe_pause validation logic
- Review implementation_state.md and recent git diff to identify any incomplete work from last session
- Fix any test failures from last Bash output and confirm test suite passes