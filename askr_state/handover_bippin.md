# Handover: bippin

Last updated: 2026-06-10 02:38

# HANDOVER DOCUMENT

## Task
Design and implement a behavioral pattern detection system for askr that automatically identifies user coding patterns (e.g., "build in stages, commit and push after each stage, show tabular view"), notifies the user when patterns are detected, and allows them to persist these patterns persistently across sessions without manual configuration.

## Status
- Decision made: CLAUDE.md is the correct persistence mechanism for global behavioral rules across all sessions
- Decision made: askr should implement automatic pattern detection that triggers notifications when user behavior matches learned patterns
- Decision made: pattern matching should be expansive and user-specific, not limited to a predefined set (user will create patterns only they know)
- Decision made: users should be able to accept/discard detected patterns via notification UI, with accepted patterns persisting automatically
- Research completed: GitHub issues #22292 and #14227 confirm this is a real, documented problem with persistent preferences in Claude Code
- Current implementation state: No code written yet; this is a feature design that was validated as needed and feasible

## Failed Approaches
- Storing behavioral patterns in askr's session_behaviors.md without user consent — rejected because it requires manual setup and doesn't capture emergent patterns
- Matching against a fixed set of predefined patterns — rejected because user patterns are unique and unknowable in advance

## Next Action
Implement pattern
