Last updated: 2026-06-08 19:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Session cost summary metrics: fixing bug where `get_session_cost_summary` reads wrong JSONL file; implementing cache hit % calculation using `cache_read_input_tokens / (cache_read_input_tokens + input_tokens)` to show actual cost savings from prompt caching.
- Phase 3.8 snapshot: defining agreed metrics (token consumption, context % used, execution time, files changed, cache hit %, input/output breakdown) for session summaries.
- Test verification: checking bash output from last session for failures and fixing any broken tests.

## Key Decisions Made

- Prompt caching metrics are viable and worth displaying; thinking tokens are not exposed by Claude Code API and cannot be extracted.
- "Savings vs projected cost" metric was incorrect and removed; cache hit % is the actionable metric instead.
- State persists in git via append-only decisions.md and JSONL session logs; session resumption injects prior context through `session_start.py` hook.
- Safe interruption validated before