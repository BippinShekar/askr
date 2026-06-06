Last updated: 2026-06-06 21:52

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Goal autonomy: Claude now launches immediately in Terminal.app with goal text as initial prompt, rather than waiting for user input. Recently fixed in lifecycle.py and cli/askr.py.
- Integration test coverage: Building 7-10 tests across all 4 stages of the checkpoint/resumption pipeline. Stage 10 (project brief generation) needs end-to-end validation with real checkpoints.
- Test suite validation: Verifying test status from recent bash output and fixing any failures before merge.

## Key Decisions Made

- Append-only decision log in decisions.md to maintain audit trail of architectural choices.
- State persisted in git (tasks, decisions, progress) rather than external database—enables offline handoffs and version history.
- Four-stage lifecycle: session start (inject context), user prompt (extract objectives), session end (generate handover docs), pre-compact (emergency checkpoint).
- Claude integration via hooks at natural session boundaries rather than polling—reduces overhead and catches exhaustion before it happens.
- Goal autonomy