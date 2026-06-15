Last updated: 2026-06-15 12:51

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across checkpoints and supporting autonomous handovers between sessions. It bridges AI suggestions with local code changes, manages subprocess execution, and integrates with Discord for notifications. The core problem it solves: enabling long-running AI-assisted development workflows that survive interruption and can resume autonomously.

## What's In Flight

- Discord webhook error handling in `askr init` — fixed return value capture and success gating; awaiting end-to-end test and commit
- Handover system architectural redesign — root cause identified as stale goal inference mid-session; requires deferring goal inference to session-end validation
- Context checkpoint card display — verifying "turns remaining" calculation displays correctly in staging before pushing report_image.py fixes
- Session state persistence improvements — treating checkpoint_pending.json and launch_mode.json as primary handover carriers rather than git diffs alone

## Key Decisions Made

- Handover state lives in checkpoint_pending.json and launch_mode.json, not git state alone — investigation revealed these files control autonomous continuation; git state is insufficient
- Goal inference deferred to session-end, not auto-inferred mid-session — auto-inference from old messages creates stale objectives that poison autonomous handovers
- Delta extraction happens at