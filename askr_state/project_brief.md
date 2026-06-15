Last updated: 2026-06-15 14:02

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state locally and supporting multi-client handovers. It bridges user commands, LLM reasoning, and file system operations through a modular architecture centered on session management, state persistence, and lifecycle hooks.

## What's In Flight

- Debugging `.env` file loading in `askr init` — friend cloned repo, manually created .env with Discord webhook key, but prompt still appears instead of auto-loading. Fixes committed: moved webhook prompt outside exception handler, updated env.py to resolve repo root from __file__ and always load .env from there. Awaiting end-to-end verification.
- Verifying context checkpoint cards display correct 'turns remaining' in staging before pushing report_image.py fixes to main.
- Architectural redesign of handover system — current checkpoint timing is fundamentally broken; goal inference must be deferred to session-end validation rather than auto-inferred mid-session to prevent stale objectives in autonomous handovers.

## Key Decisions Made

- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone — investigation revealed these files control autonomous session continuation.
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting