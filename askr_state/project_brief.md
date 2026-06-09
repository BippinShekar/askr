Last updated: 2026-06-10 03:02

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent developer context, active objectives, and coding patterns—so work can resume without losing momentum or repeating decisions.

## What's In Flight

- Behavioral pattern detection system: automatically identifying user coding patterns, confirming them via Cursor popup or Discord webhook (for headless), and persisting them to `~/.claude/CLAUDE.md` or project-specific `.claude/CLAUDE.md`
- Implementation of `behavior_confirm` notification type in Cursor mode using existing `goal_check` infrastructure
- Discord integration for headless environment notifications (one-way, no response channel required)
- Test verification and fix of any failures from last session output

## Key Decisions Made

- Two-mode notification system: interactive `behavior_confirm` popup in Cursor (keep/discard buttons), Discord webhook in headless (one-way notification only)
- Expansive user-specific patterns, not fixed set: users create patterns only they know; system learns from behavior rather than enforcing predefined rules
- Pattern persistence in global or project-specific `.claude/CLAUDE.md` files, keyed by user confirmation
- Reuse existing