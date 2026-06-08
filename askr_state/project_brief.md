Last updated: 2026-06-08 19:07

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Fixing incorrect cost and token metrics in Discord session summary cards. Root cause identified: `get_state_dir()` was reading the wrong project path. Fix applied to `askr/state/config.py` but `get_session_cost_summary()` is still reporting implausible values (~$140, 500+ turns for single goal execution).
- Verifying test status from last bash output and fixing any failures.
- Reviewing files changed since last session against decisions.md.

## Key Decisions Made

- State is append-only and stored in git. Decisions are logged with timestamp, developer, and reason; existing lines are never edited.
- Session lifecycle is split across four modules: monitoring (token forecasting), hooks (Claude Code integration points), state persistence (reader/writer), and QA (context analysis).
- Hooks inject context at session start, extract objectives from user prompts, generate handover docs on stop, and emergency checkpoint before context auto-compaction.
- Safe interruption is validated before checkpoint to avoid corrupting