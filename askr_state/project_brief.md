Last updated: 2026-06-15 16:42

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across restarts and supporting autonomous continuation. It bridges code editors, subprocess execution, and language models to enable hands-off coding workflows where the AI can pick up where a human left off.

## What's In Flight

- Phase 3.12 directional inference: Fixed two critical bugs in lifecycle.py that were preventing proper signal weighting (blockers.md metadata filtering, git momentum regex). System now correctly infers session direction from three signals: blocker count, file recency, and git momentum. Validated end-to-end.
- Integration of directional inference into stop-hook handover generation: Currently inference runs standalone; next step is to feed its output into checkpoint creation so autonomous sessions use dynamic direction instead of static prompts.
- Confidence threshold validation: 0.70 threshold needs real multi-session testing before full autonomous deployment.
- Multi-file context extension: Current inference assumes single active file; real sessions juggle multiple files.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause was logic gap where stop checkpoint handler was never invoked, not timing issues.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session. Auto-