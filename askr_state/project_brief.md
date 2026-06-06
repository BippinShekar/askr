Last updated: 2026-06-06 23:16

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It solves the problem of losing work and context mid-session when Claude's limits reset, enabling seamless handoffs between developers and session resumptions.

## What's In Flight

- Twitter problem-statement post finalized and ready to publish: "claude makes you cracked at building. then quota hits. train of thought gone. flow gone. anyone else?"
- Session lifecycle management: checkpoint and resumption flow working end-to-end with Terminal.app fallback for notifications
- Phase 1 clarification: `ask` is the natural language Q&A CLI; `askr` is the session orchestration daemon with subcommands only
- Verification of test status from last bash output and fixing any failures

## Key Decisions Made

- Notification flow always launches Terminal.app as fallback, regardless of VS Code notification pickup (ensures visibility)
- Tweet stays problem-focused, not product-focused, to engage followers before revealing the solution
- Phase 1 scope: session monitoring, checkpoint generation, and basic resumption; full multi-developer handoff is Phase 2+
- State persisted in git via append-only decision log and handover documents for transparency and auditability
- Context forec