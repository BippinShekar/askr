Last updated: 2026-06-14 14:38

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with LLM integration, state persistence, and multi-client support. It solves the problem of context loss and manual handoff between development sessions by persisting session state, tracking token usage, and enabling autonomous continuation across interruptions.

## What's In Flight

- Phase 5 (Hardening): Integrating approval gate for queued tasks. Gate triggers when dangerous permissions are enabled (--dangerously-skip-permissions, unrestricted Bash, file deletion), blocking execution until confirmed.
- Phase 7 (Team Scale): Restructuring flat file state layout to support 50+ concurrent developers. Stage P7-0 defines new team-scoped directory structure (teams/<team>/members/<dev>/) with migration path. Stage P7-1 (task queuing) was cut off mid-draft and needs completion.
- Staging verification: Checkpoint card display for 'turns remaining' needs validation before main branch push.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes. Root cause is that stop checkpoint handler is never invoked, creating stale handovers—not a race condition.
- Goal inference must be session-aware and deferred until session-end validation. Auto-inferring from old messages creates stale objectives that