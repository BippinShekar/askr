Last updated: 2026-06-14 14:44

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with an LLM, managing code changes, test validation, and state persistence across multiple client sessions. It solves the problem of context loss and manual handoff overhead when developers need to pause, resume, or hand off coding tasks to teammates or autonomous agents.

## What's In Flight

- Completing Phase 4 (Team Scale) roadmap section: finishing P4-2 (askr team CLI) feature table and adding completion criteria
- Committing three roadmap.md changes that restructure phases: moving approval gate to Phase 5, renaming Phase 4 from Public Launch to Team Scale, pushing public launch to Phase 7, and removing premature migration overhead
- Verifying context checkpoint cards display correct 'turns remaining' calculation in staging environment before pushing report_image.py fixes to main
- Reviewing Phase 5 (Hardening) to confirm approval gate placement doesn't conflict with other hardening features and lands before Phase 7 task queuing

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes—stale checkpoints are a fundamental timing issue where the stop checkpoint handler is never invoked, not a data formatting problem
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid