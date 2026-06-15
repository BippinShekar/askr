Last updated: 2026-06-15 14:13

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, tracks usage metrics, and integrates with IDEs (VSCode, JetBrains) to provide code analysis and assistance. It persists session state locally and manages autonomous handovers between sessions so work can resume without context loss.

## What's In Flight

- Fixing checkpoint handover system: stale goals and missing stop-checkpoint handlers are causing autonomous sessions to resume with outdated context. Root cause identified as logic gap, not timing issue. Requires architectural redesign of goal inference timing.
- Verifying context checkpoint cards display correct "turns remaining" in staging environment before pushing report_image.py fixes to main.
- Resolving .env loading order in askr init: friend's Discord webhook URL wasn't being registered because ~/.config/askr/.env was loaded first, blocking repo .env. Fix committed; awaiting verification after git pull.

## Key Decisions Made

- Checkpoint system treats checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone. Investigation revealed these files control autonomous session continuation.
- Goal inference deferred to session-end validation, not auto-inferred mid-session. Auto-inferred goals become stale and poison autonomous handovers; inference must be session-aware, not message-aware