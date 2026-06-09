Last updated: 2026-06-10 03:08

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so work can resume without losing context or re-granting permissions.

## What's In Flight

- Permission persistence across sessions: `askr init` now seeds both `allowedTools` and `permissions.allow` with baseline tools including WebSearch, so users don't re-grant permissions on resumption.
- Verification that fresh init creates properly populated `settings.local.json` and that permissions persist across session boundaries without re-prompting.
- Test status review from last session output and fixing any failures.

## Key Decisions Made

- State is append-only in git (decisions.md, handover docs) to maintain audit trail and enable easy rebasing across sessions.
- Session lifecycle is split into five stages: monitor (token tracking), forecast (predict which limit hits first), checkpoint (persist before exhaustion), safe_pause (validate interruption points), and lifecycle (trigger resumption).
- Baseline allowed tools (including WebSearch) are seeded during init to avoid repeated permission prompts across session boundaries.
- Handover documents are generated on session end and committed automatically, making context transfer