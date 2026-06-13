Last updated: 2026-06-13 23:14

# Project Brief

Askr is a CLI-based AI coding agent that solves context loss across Claude sessions. When you switch machines or start a new Claude conversation, you lose all the context about what you were building—Askr captures session state, goals, and code deltas, then hands them off seamlessly so Claude picks up exactly where you left off without re-explaining everything.

## What's In Flight

- **Handover system redesign** — Root cause identified: stop checkpoint handler never invokes, leaving handover stale. Requires architectural fix to ensure checkpoints capture final session state before autonomous continuation.
- **Goal inference timing** — Moving from message-aware (stale) to session-aware inference; goals must be validated at session-end, not auto-inferred mid-session.
- **Context checkpoint display** — Verifying "turns remaining" calculation displays correctly in staging before pushing report_image.py fixes to main.
- **Launch messaging** — Drafting authentic launch tweet that leads with pain point (context loss across sessions) without revealing product; curating follow list for organic reach. One week to public launch.

## Key Decisions Made

- Checkpoint system treats both dict and str goal formats for backward compatibility while supporting new JSON serialization.
- Delta extraction happens at hook level (post_tool_use.py), not checkpoint.py—separates concerns between raw