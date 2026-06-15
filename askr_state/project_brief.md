Last updated: 2026-06-15 13:05

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting multi-client handovers. It lets developers delegate coding tasks to Claude, track progress across sessions, and resume work from checkpoints. The core problem it solves: managing long-running AI-assisted development workflows without losing context or progress.

## What's In Flight

- Fixing Discord webhook configuration in local .env files. Root cause identified: env.load() was returning early after loading global config, blocking local .env from being read. Fix committed and pushed (env.py and askr.py).
- Verifying context checkpoint cards display correct "turns remaining" in staging environment before pushing report_image.py fixes to main.
- Architectural redesign of the handover system. Current behavior is failing catastrophically: checkpoints become stale because goal inference happens mid-session and the stop checkpoint handler is never invoked. Goal inference must be deferred to session-end validation and made session-aware, not message-aware.

## Key Decisions Made

- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone. Investigation showed these files control autonomous session continuation.
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serial