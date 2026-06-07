Last updated: 2026-06-07 21:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Rich spinner UI on `askr init` command during architecture.md generation (Haiku API call on large repos, 20-30 second bottleneck). Implementation complete; awaiting verification on large repository.
- Test status verification and failure fixes from last session output.
- Review of files changed since last session and decisions.md alignment.

## Key Decisions Made

- State persisted to git (not database) to enable developer handoffs and version history.
- Modular architecture: session lifecycle, Claude Code hooks, persistent state layer, and code analysis as separate concerns.
- Checkpoint triggered before context auto-compaction and on session end; resumption injects prior context on session start.
- Architecture snapshot generation via Haiku API (cost-effective, acceptable latency for initialization).
- Append-only decisions.md log (never edit existing lines) to maintain audit trail.

## Open Goals

- Verify spinner implementation works on large repository without blocking workflow.
- Fix any test failures from last session.
- Ensure decisions.