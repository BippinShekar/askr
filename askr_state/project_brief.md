Last updated: 2026-06-15 13:05

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across invocations and supporting multi-client execution. It bridges IDE/editor communication, manages subprocess execution, and maintains session history for autonomous handovers between runs.

## What's In Flight

- Fixing checkpoint handover system: stale goals and missing session-end validation are causing autonomous continuations to fail. Root cause identified as logic gap where stop checkpoint handler is never invoked; goal inference must be deferred to session-end, not auto-inferred mid-session.
- Verifying context checkpoint cards display correct "turns remaining" in staging before pushing report_image.py fixes to main.
- Discord webhook initialization bug fixed (env.py and askr.py); awaiting user verification that local .env is now picked up correctly.

## Key Decisions Made

- Checkpoint system treats checkpoint_pending.json and launch_mode.json as primary handover state carriers, not git diffs alone. Investigation revealed these files control autonomous session continuation.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred from old user messages mid-session. Auto-inferred goals become stale and poison autonomous handovers.
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while