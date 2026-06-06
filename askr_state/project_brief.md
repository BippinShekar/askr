Last updated: 2026-06-06 23:16

# Project Brief

Askr is a daemon and CLI tool that solves context loss when Claude Code sessions hit quota or context limits mid-workflow. It monitors token usage, predicts which limit will be exhausted first, automatically checkpoints project state to git before interruption, and orchestrates seamless resumption so developers never lose their train of thought or progress.

## What's In Flight

- Twitter/X post about the core problem (draft finalized, awaiting publication)
- Fallback mechanism for session resumption notifications: write notification AND launch Terminal.app; if Terminal.app fails, run headless
- CLI structure: `askr` handles subcommands (goal, status, goals); `ask` handles natural language Q&A (Phase 0)
- Integration hooks with Claude Code: session_start, user_prompt_submit, stop, pre_compact

## Key Decisions Made

- State persisted to git as append-only decision log and handover documents; enables developer handoffs and session resumption without external databases
- Checkpoint triggered before exhaustion, not after; safe_pause validates interruption points to avoid mid-operation breaks
- Dual notification path (notification + Terminal.app + headless fallback) ensures resumption prompt reaches developer regardless of environment
- Natural language Q&A uses `ask` command, not `askr`; `askr` reserved for structured sub