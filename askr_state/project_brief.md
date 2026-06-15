Last updated: 2026-06-15 14:25

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across interruptions and supporting autonomous continuation. It manages subprocess execution, multi-client LLM integration, and handover state to allow sessions to resume without losing context or objectives.

## What's In Flight

- macOS SSL certificate verification fix in Discord webhook client — certifi integration staged and ready for final commit
- Context checkpoint card display validation in staging — verifying 'turns remaining' calculation displays correctly before pushing to main
- Handover system architectural redesign — current implementation has fundamental timing issues where stale checkpoints are created; requires rethinking when goal inference happens and how stop handlers are invoked
- Goal inference timing fix — shifting from message-aware auto-inference (which becomes stale) to session-aware inference deferred until session-end validation

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone — these files control autonomous continuation and are the primary source of truth for session recovery
- Goal inference must be session-aware and deferred to session-end, not auto-inferred from old user messages mid-session — prevents stale objectives from poisoning autonomous handovers
- Root cause of stale checkpoints is a logic gap where the stop checkpoint handler is never invoked