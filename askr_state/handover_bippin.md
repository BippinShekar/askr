# Handover: bippin

Last updated: 2026-06-10 03:02

# Handover Document

## Task
Design and implement a behavioral pattern detection system for askr that automatically identifies user coding patterns, notifies the user with confirmation UI, persists confirmed patterns, and extends to headless environments via Discord.

## Status
- Roadmap.md updated with Phase 3.9: Behavioral Pattern Detection
- Design decision finalized: two-mode notification system
  - Cursor mode: `behavior_confirm` popup with keep/discard buttons (uses existing `goal_check` infrastructure)
  - Headless mode: Discord webhook notification (one-way, no response channel)
- Core problem validated: GitHub issues #22292 and #14227 confirm users need persistent behavioral preferences
- Pattern detection approach settled: expansive user-specific patterns (not fixed set) — user creates patterns only they know
- Discord integration already exists in askr; reuse for headless notifications
- Persistence mechanism: patterns confirmed by user stored in `~/.claude/CLAUDE.md` (global) or project-specific `leaps/.claude/CLAUDE.md`

## Failed Approaches
- Fixed pattern set: rejected because user patterns are unique and unknowable in advance
- Single-mode notification: rejected because headless environments cannot receive interactive confirmations; two-mode design required

## Next Action
Implement `behavior_confirm` notification type in Cursor mode
