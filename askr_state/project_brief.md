Last updated: 2026-06-06 21:43

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Autonomous session auto-launch: `askr goal add` now immediately starts a new Claude session without manual intervention. End-to-end flow verified; awaiting final demo confirmation.
- Integration test suite for all 4 checkpoint/resumption stages (7-10 tests) in CI pipeline.
- Stage 10 project brief generation end-to-end validation with real checkpoint data.
- Review of files changed since last session and verification against decisions log.

## Key Decisions Made

- State persists in git as append-only decision log and task/progress files; enables full audit trail and cross-developer handoffs.
- Session lifecycle split into four stages: monitor (detect exhaustion), forecast (predict which limit hits first), checkpoint (safe pause and commit), resume (inject context on restart).
- Claude Code integration via hooks at session start, user prompt submit, session stop, and pre-compaction; allows non-invasive monitoring.
- Auto-launch on `goal add` always creates new session; no check for existing session to