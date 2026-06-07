Last updated: 2026-06-07 08:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, preventing work loss, and eliminating manual interruption overhead.

## What's In Flight

- Phase 3.7: Rich visual Discord reports showing context compression savings per session. Generates matplotlib PNG visualizations with token/cost deltas (askr vs. without), context timeline bars, and concrete value prop. Sends directly via Discord webhook multipart/form-data.
- Phase 4: Settings inheritance for auto-spawned Claude Code sessions. Child sessions must inherit parent session permissions and configuration instead of requiring re-entry.
- Context trigger stress testing: Need deliberate test to verify 75% context limit detection works on small sessions (may temporarily drop CONTEXT_TRIGGER to 0.3 in lifecycle.py to force exhaustion).

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files. Enables full audit trail and developer handoffs.
- Checkpoint triggered before context auto-compaction (pre_compact.py hook) and on safe pause points validated by safe_pause.py.
- PNG visualization approach chosen over text reports or screenshots for impact and clarity on savings.