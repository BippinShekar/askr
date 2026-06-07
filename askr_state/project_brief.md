Last updated: 2026-06-08 02:04

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, solving the problem of losing work and context when Claude Code sessions hit their limits.

## What's In Flight

- Rolling window context implementation for `ask` CLI: loads last 5 conversation exchanges from `.askr_history` and injects them into prompt context to maintain conversation history across stateless invocations. Implementation complete and committed.
- Tweet draft about Claude's auto-compaction quota burn: analysis shows auto-compaction consumes 4-5% of the 5-hour quota window silently. Draft needs revision to end with a question and adopt conversational tone rather than technical framing.
- Test status verification: need to check latest Bash output for any test failures and fix.

## Key Decisions Made

- State persistence via git: all session state, decisions, and progress tracked in append-only decision logs and handover documents committed to git, enabling developer handoffs without context loss.
- Modular hook architecture: Claude Code integration points (session start, prompt submit, session stop, pre-compaction) implemented as discrete hooks rather than monolithic integration, allowing targeted intervention at critical moments.
- Stat