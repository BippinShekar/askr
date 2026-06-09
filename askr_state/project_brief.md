Last updated: 2026-06-10 02:38

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent developer context, task history, and decisions in version control.

## What's In Flight

- Behavioral pattern detection system: automatically identify user coding patterns (e.g., "build in stages, commit after each stage"), notify users when patterns are detected, and persist accepted patterns across sessions without manual configuration.
- Pattern persistence mechanism: using CLAUDE.md as the global behavioral rules store across all sessions.
- Test verification and failure fixes from last session output.
- Review of files changed since last session and decision log updates.

## Key Decisions Made

- State persistence uses git-backed files (CLAUDE.md for global rules, session_behaviors.md for session-specific context) rather than external databases, enabling offline handoffs and full version history.
- Pattern detection is expansive and user-specific, not limited to predefined patterns, because user behaviors are unique and unknowable in advance.
- Users accept or discard detected patterns via notification UI; accepted patterns persist automatically without requiring manual configuration.
- Behavioral patterns are learned from user actions during sessions, not configured upfront.

## Open Goals

- Implement pattern detection system that triggers notifications when