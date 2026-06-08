Last updated: 2026-06-08 18:37

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It maintains developer context and task continuity across session boundaries, enabling seamless handoffs between developers and resumption of work without losing progress or context.

## What's In Flight

- Fixing state directory resolution bug: `get_state_dir()` was reading from globally stored leaps path instead of current project path, causing hooks to read/write state to wrong directory. Fix applied to `askr/state/config.py` with commit "fix: get_state_dir".
- Debugging Discord notification failures: stop hook not firing when goals complete. Root cause traced to state directory bug cascading across session lifecycle (goal inference, handover persistence, hook execution).
- Verifying test status and fixing any failures from last bash output.

## Key Decisions Made

- State is persisted in git as append-only decision logs and markdown files (goals.md, progress.md, decisions.md) rather than databases. Enables human-readable handoffs and version control.
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion rather than after.
- Hooks integrate at four critical points: session start (inject context), user prompt submit (