Last updated: 2026-06-14 10:06

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across checkpoints and supporting autonomous handovers between sessions. It integrates with IDEs, executes code via subprocess, and tracks session progress through hooks and state snapshots. The core problem it solves: enabling AI to continue complex coding tasks across multiple sessions without losing context or progress.

## What's In Flight

- Removing misleading analytics metrics from CLI output (time saved, goals completed without explicit tracking). 45% complete. Next: audit askr.py to confirm 'time saved' is fully removed and design explicit goal completion tracking schema.
- Fixing checkpoint handover system. Root cause identified: stop checkpoint handler is not invoked, causing stale checkpoints. Requires architectural redesign, not incremental fix. Goal inference must be deferred to session-end validation, not auto-inferred mid-session.
- Verifying context checkpoint cards display correct 'turns remaining' in staging environment before pushing report_image.py fixes to main.

## Key Decisions Made

- Checkpoint and launch_mode.json are primary handover state carriers, not git diffs alone. Investigation revealed these files control autonomous session continuation.
- Handle both dict and str goal formats in checkpoint.py for backward compatibility with existing checkpoints while supporting new JSON-serialized format.