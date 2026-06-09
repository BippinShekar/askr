Last updated: 2026-06-10 00:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context.

## What's In Flight

- Context-aware restart mechanism: ensuring project_path and allowed_tools flow through the notification chain from lifecycle manager to extension terminal handler. Three files staged and ready to commit: lifecycle.py, stop.py, extension.js.
- Emergency checkpoint implementation: completing the safe_pause validation logic that detects safe interruption points before context auto-compaction.
- Test suite verification: fixing any failures from recent changes and ensuring all modules pass.

## Key Decisions Made

- State persisted to git, not a database. Enables offline handoffs and version control of developer context.
- Checkpoint triggered by forecast, not by hard limit hit. Proactive rather than reactive—predicts which limit (context or quota) will be exhausted first.
- Extension-daemon split: Claude Code extension handles terminal creation and session lifecycle hooks; daemon handles monitoring and state orchestration. Notification.json is the contract between them.
- Append-only decisions log. Never edit past decisions; new decisions always appended with timestamp and reasoning.