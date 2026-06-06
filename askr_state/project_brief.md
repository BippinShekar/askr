Last updated: 2026-06-06 21:27

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before those limits are hit. This enables seamless handoffs between developers and sessions—when Claude Code runs out of context, Askr has already saved the work and can resume it in a fresh session without losing progress.

## What's In Flight

- Fixing the context trigger checkpoint mechanism: the Stop hook was not firing because the daemon writes `checkpoint_pending.json` but had no mechanism to kill the Claude process. Solution implemented in `lifecycle.py` with `_wait_for_exchange_end_then_kill` function that polls for quiet state then kills Claude to trigger the hook. Changes committed; daemon reloaded.
- Integration tests for all 4 stages (7-10) in CI pipeline—currently incomplete.
- End-to-end test of Stage 10 project brief generation with a real checkpoint.
- Verification of test status and fixing any failures from last Bash output.

## Key Decisions Made

- State is persisted in git, not a database, to enable developer handoffs and version control of context.
- Checkpoint happens before exhaustion, not after—forecasting predicts which limit hits first (context or quota) and triggers early.
- Stop hook (on Claude