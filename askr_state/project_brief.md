Last updated: 2026-06-08 19:19

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, so work can resume without losing progress or context.

## What's In Flight

- Phase 3.8 session card metrics refinement: identifying which metrics actually reflect Askr's autonomous value (files changed, duration confirmed; cost savings calculation and cache hit % under review)
- Cost savings calculation bug: currently reads wrong session JSONL file (most recently active instead of Phase 3.8's actual session)
- Verification of test status from last bash output and fixing any failures
- Review of files changed since last session and cross-check against decisions.md

## Key Decisions Made

- Cache hit % metric rejected from card display: Anthropic's infrastructure manages caching automatically; Askr has no control over it, so displaying it implies false credit for efficiency gains
- Thinking tokens cannot be displayed: Claude Code's usage object does not expose thinking token counts, making percentage calculations impossible
- State persistence via git: all session context, tasks, and decisions stored in append-only decision logs and state files to enable developer handoffs
- Safe pause validation required before checkpoint: `safe_pause.py` ensures interruption only