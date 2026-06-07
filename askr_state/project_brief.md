Last updated: 2026-06-08 02:01

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Rolling window context implementation for `ask` CLI tool: loads last 5 history exchanges on each invocation to preserve conversation history without in-memory overhead. Completed and verified working.
- Quota analysis: eliminated ~4-5% quota waste from context compaction by switching to rolling window approach.

## Key Decisions Made

- Rolling window (load last 5 exchanges per invocation) chosen over in-memory retrieval: CLI tool spawns fresh process each time, so in-memory state is lost; rolling window avoids re-embedding overhead and works with stateless architecture.
- State persisted to git via append-only decision log and state files (tasks, progress, context snapshots) to enable developer handoffs.
- Checkpoint triggered before context auto-compaction and on session end to prevent state loss.
- Hook-based integration with Claude Code: session start injects context, user prompts extract objectives, session stop generates handover docs.

## Open Goals

- Verify test status from last Bash output and