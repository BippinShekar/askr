Last updated: 2026-06-07 22:04

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Rolling window conversation history: injecting last 5 interactions from `.askr_history` into `ask` CLI queries so multi-turn conversations can reference prior context without in-memory state. Implementation complete in `pipeline.py`; awaiting end-to-end verification.
- Test status verification: confirm all tests pass after recent history injection changes.
- File review: audit changes since last session and validate against decisions log.

## Key Decisions Made

- Rolling window history over in-memory retrieval: CLI is stateless per invocation, so storing conversation in `.askr_history` file and loading on each query is faster than re-embedding history every time.
- State persisted to git: all checkpoints, decisions, and progress tracked in version control to enable true handoffs between developers.
- Haiku LLM for architecture generation: lightweight model used for generating `architecture.md` snapshots during session analysis.
- Safe pause validation: interruption only allowed at safe points (no mid-function-call) to