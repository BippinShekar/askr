Last updated: 2026-06-11 12:45

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or repeating analysis.

## What's In Flight

- Diagnosing and fixing session kill during extended thinking: context window threshold being increased from 50% to 65% per chat in lifecycle.py to prevent premature termination.
- Daemon restart detection to prevent stale code execution after daemon restarts.
- Auto-continue switch verification in askr repo after daemon trigger.
- Test suite validation and failure fixes from last Bash output.
- Discord update message generation with sample session card image.
- Decision: display git remote or directory name in card top-right.

## Key Decisions Made

- Session state persisted in git (not database) to enable developer handoffs and version control integration.
- Append-only decision log in decisions.md prevents accidental loss of reasoning history.
- Context exhaustion predicted before it happens, not reacted to after—allows graceful checkpoint before Claude Code auto-compacts.
- Hooks into Claude Code lifecycle (session_start, user_prompt_submit, stop, pre_compact) rather