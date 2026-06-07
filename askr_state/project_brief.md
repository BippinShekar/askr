Last updated: 2026-06-07 21:49

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—tasks, decisions, progress—so work can resume without losing context or repeating analysis.

## What's In Flight

- Progress/ETA indicators for `askr init` command when initializing large repositories. Current implementation shows step-by-step listing but lacks visual feedback for long operations.
- Verification that Claude Code's native auto-compact progress bar is not a useful data source for askr monitoring (confirmed: it only appears in repos without askr, where askr's preventative firing at 75% context would never allow it to trigger).
- Bash grep search results pending review to audit current implementation for existing progress/spinner/ETA/status tracking in cmd_init and related functions.

## Key Decisions Made

- Askr fires preventatively at 75% context exhaustion to avoid triggering Claude Code's native auto-compact. This design means askr-enabled repos never reach the state where Claude's progress bar appears.
- State is append-only in decisions.md; historical decisions are never edited, only new ones appended with timestamp and reasoning.
- Session state persists in git via checkpoint commits,