Last updated: 2026-06-10 03:06

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so any developer can resume work without losing context.

## What's In Flight

- Phase 3.9: Behavior pattern detection with user confirmation. Cursor sessions use interactive popups (existing infrastructure); headless sessions notify via Discord webhook (one-way receipt, no blocking).
- Phase 3.8 fix: `askr init` now seeds `permissions.allow` with baseline allowed tools to `settings.local.json`, so permission carry-on works from session two onward.
- Permission system validation: Confirmed that persisted rules in `~/.claude/CLAUDE.md` are read correctly by subsequent sessions.

## Key Decisions Made

- Two-mode confirmation design: Cursor uses `behavior_confirm` notification type with action buttons; headless uses Discord webhooks. Unified flow rejected because headless cannot block on user input.
- State persistence via git: All session state (tasks, decisions, progress) stored in version control to enable developer handoffs and audit trail.
- Permission carry-on: Rules persist in `~/.claude/CLAUDE.md` after first