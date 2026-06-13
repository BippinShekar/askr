Last updated: 2026-06-13 23:55

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, manages code context, generates and validates code, and hands over work to autonomous continuation. It integrates with IDEs, tracks session costs, and persists state across invocations. The core problem: developers need an agent that understands their codebase, generates code incrementally, and can resume work without losing context.

## What's In Flight

- Cost tracking and session metrics display. Added log_line_mark() and cost_since_mark() helpers to logger.py; wired into cmd_init() to show cost after Discord brief resolves. Currently investigating how 'time saved' and 'sessions today' metrics are calculated in askr status command.
- Handover system redesign. Root cause identified: stop checkpoint handler is never invoked, leaving handovers stale. Goal inference must be deferred to session-end validation and made session-aware, not message-aware, to prevent auto-inferred goals from poisoning autonomous continuation.
- Context checkpoint card display verification. Need to confirm 'turns remaining' calculation displays correctly in staging before pushing report_image.py fixes to main.

## Key Decisions Made

- Checkpoint system accepts both dict and str goal formats for backward compatibility while supporting new JSON-serialized format.
- Delta extraction happens at hook level (post