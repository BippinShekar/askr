Last updated: 2026-06-11 19:42

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. When a session ends, it generates handover documentation so another developer (or the same developer in a new session) can resume work without losing context or progress. The core problem: Claude Code sessions are stateless and ephemeral; Askr makes them persistent and transferable.

## What's In Flight

- Investigating how Claude CLI accepts positional arguments to pass session context and state when resuming after quota exhaustion. Current blocker: need to review bash command output from extension file inspection to determine the mechanism for context injection into new Claude instances.
- Building Discord integration to surface session cards and status updates.
- Validating test suite and fixing any failures from recent changes.
- Reviewing files changed since last session and cross-referencing against decisions log.

## Key Decisions Made

- State is append-only and stored in git. Decisions are immutable once logged; new decisions are appended with timestamp and reasoning.
- Session lifecycle is managed through Claude Code hooks: session_start injects context, user_prompt_submit captures objectives, stop generates handover docs and commits state, pre_compact triggers emergency checkpoints.
- Persistent state lives in askr/state/ with separate readers and writers; config