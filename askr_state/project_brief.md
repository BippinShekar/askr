Last updated: 2026-06-15 14:30

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting multi-client integrations. It solves the problem of context loss in AI-assisted coding by maintaining session state, tracking token usage, and enabling autonomous continuation of work across multiple invocations.

## What's In Flight

- Fixing macOS SSL certificate verification in Discord webhook client by adding certifi library for proper SSL context
- Verifying checkpoint card display shows correct "turns remaining" calculation in staging environment
- Ensuring multi-project setup works correctly so users can run `askr init` per-repo for separate credential tracking (private vs official projects)
- Architectural redesign of handover system to fix stale checkpoint issue where goal inference happens mid-session instead of at session-end validation

## Key Decisions Made

- Handover state is carried by checkpoint_pending.json and launch_mode.json, not git diffs alone—these files control autonomous session continuation
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred from old user messages mid-session
- Root cause of stale handovers is a logic gap where the stop checkpoint handler is never invoked, not a race condition
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints
-