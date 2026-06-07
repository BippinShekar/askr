Last updated: 2026-06-07 22:00

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Implement in-memory tokenization and retrieval system for `.askr_history` conversation context in the `ask` CLI tool. Currently every query starts fresh and ignores prior conversation history stored in `.askr_history`.
- Integrate conversation history into LLM prompts during query execution by modifying the query handler in `askr/cli/askr.py`.
- Verify test status from last session and fix any failures.

## Key Decisions Made

- State is persisted to git as append-only decision logs and task snapshots, enabling handoffs between developers without manual context transfer.
- Session monitoring uses token forecasting to predict which limit (context or quota) will be hit first, triggering proactive checkpoints before exhaustion.
- Claude Code integration happens via hooks at session start, prompt submission, session end, and pre-compaction, allowing Askr to inject context and extract objectives without modifying Claude's core behavior.
- In-memory token-aware retrieval was chosen over rolling window approach for conversation history