Last updated: 2026-06-06 18:03

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Secrets scrubbing in session transcripts: `_scrub_secrets()` function masks Discord webhooks, API keys, and tokens before transcripts reach Claude. Wired into checkpoint pipeline and documented in README.
- Integration test suite for all 4 stages (7-10) in CI pipeline. Stage 10 (project brief generation) needs end-to-end verification with real checkpoint data.
- Test status verification: need to check last Bash output for failures and fix any broken tests.

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of architectural choices.
- State persisted to git via checkpoint.py before exhaustion, enabling developer handoffs without manual intervention.
- Four-stage lifecycle: monitor token usage → forecast which limit hits first → safe pause at valid interruption point → generate handover docs and commit.
- Secrets scrubbing happens at transcript generation time, not at session capture, to avoid data loss while protecting Claude API calls.