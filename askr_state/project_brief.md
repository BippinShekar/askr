Last updated: 2026-06-07 21:57

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Spinner progress indicator for `askr init` architecture generation on large repositories (completed, committed)
- Investigation into context-aware assistance not functioning despite context being available in `.askr_history`
- Verification of test status and fixing any failures from last session
- Review of files changed since last session against decisions.md

## Key Decisions Made

- State is persisted to git as append-only decision logs and task files, enabling handoffs between developers
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion
- Claude Code integration happens via hooks at session start, prompt submission, session stop, and pre-compaction
- Architecture generation during init uses Haiku LLM call (20-30s on large repos); spinner-only UX is sufficient, no ETA needed
- Implementation state generation is instant file manipulation; no spinner required

## Open Goals

- Fix any test failures from last Bash output
- Diagnose why context-aware assistance is not working despite