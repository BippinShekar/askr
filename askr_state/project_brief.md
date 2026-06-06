Last updated: 2026-06-06 22:11

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control. The core problem: Claude Code sessions are stateless and ephemeral; Askr makes them durable and transferable.

## What's In Flight

- Phase 3.5 guard implementation (complete): Pre-tool-use hook intercepts Claude's actions, validates against safety rules, logs violations to guard_log.md, and delivers alerts to IDE and Discord.
- Phase 3.6 (staged roadmap): Autonomous guard correction with Discord feedback loop—guard will send error screenshots, reinject context, auto-correct Claude's mistakes, and escalate to Discord after 2 failed retries.
- End-to-end testing: Verifying all 4 checkpoint/resumption stages (7-10) work with real Discord screenshots and project brief generation.
- CI pipeline: Adding integration tests for stages 7-10 to catch regressions.

## Key Decisions Made

- State persisted to git, not a database—enables offline handoffs and full audit trail via commits.
- Hook-based architecture into Claude Code lifecycle (session_start, user_prompt