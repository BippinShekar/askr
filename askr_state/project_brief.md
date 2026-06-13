Last updated: 2026-06-13 23:18

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive Claude sessions across machines, handling context limits, token quota checkpoints, and session state persistence. It solves the pain of losing work context when switching machines or hitting Claude's session boundaries—users can now hand off incomplete tasks to autonomous continuations without re-explaining their progress.

## What's In Flight

- Twitter/X launch messaging: sarcasm-driven tweet about repetitive Claude handoffs paired with Homelander meme image. Ready to post; spacing decision pending (spaced vs compact layout on mobile).
- Phase 3.11 JSON Handover Schema: finalizing checkpoint card display logic to show correct "turns remaining" before staging verification.
- Stress-tests/ directory: load and performance testing suite to validate session continuity under quota pressure.
- GitHub launch assets: README with GIF/screenshot, install story, changelog, and release notes (one week to public launch).

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause is that stop checkpoint handler was never invoked—stale checkpoints are a logic gap, not a timing race.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session. Auto-inferred goals from old messages become stale and poison autonomous handovers