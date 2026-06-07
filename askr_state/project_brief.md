Last updated: 2026-06-07 22:06

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so any developer can resume work without losing context.

## What's In Flight

- Rolling window context for `ask` CLI: injecting last 5 conversation exchanges from `.askr_history` into query prompts to reduce context compaction and preserve quota. Implementation committed; currently quantifying token/quota savings vs. baseline.
- Test verification: checking Bash output for test failures and fixing any blockers.
- Session state review: analyzing files changed since last session and cross-referencing decisions.md.

## Key Decisions Made

- State persisted to git, not in-memory: enables handoffs and survives process restarts.
- Append-only decisions log: decisions are never edited, only appended, to maintain audit trail.
- Rolling window over in-memory retrieval: rejected embedding-on-every-call approach; rolling window is faster for CLI tool where each invocation is a fresh process.
- Hook-based integration with Claude Code: session lifecycle tied to start, prompt submit, stop, and pre-compact events rather than polling.

## Open Goals

- Quantify actual