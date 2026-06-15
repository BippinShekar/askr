Last updated: 2026-06-15 12:38

# Project Brief

Askr is a CLI-based AI coding assistant that manages user sessions, tracks usage, and integrates with IDE environments and external AI providers. It solves the problem of fragmented AI-assisted development by providing a unified interface for session management, context tracking, and autonomous handover between work sessions.

## What's In Flight

- Discord webhook send failure in askr init — return value was being ignored, causing false success messages. Fix is implemented and pending test on real environment.
- Roadmap.md Phase 4 restructuring — P4-2 (askr team CLI) table needs completion and phase completion criteria need to be added.
- Context checkpoint card display verification in staging — need to confirm 'turns remaining' calculation displays correctly before pushing report_image.py fixes to main.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause is that the stop checkpoint handler is never invoked, making stale checkpoints a fundamental timing issue, not a data formatting problem.
- Goal inference must be session-aware and deferred until session-end validation, not auto-inferred mid-session. Auto-inferred goals from old messages become stale and poison autonomous handovers.
- Treat checkpoint_pending.json and launch_mode.json as primary handover state carriers. Investigation revealed these files control autonomous session continuation;