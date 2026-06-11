Last updated: 2026-06-11 20:25

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, solving the problem of lost context and wasted work when long-running AI coding sessions hit resource limits.

## What's In Flight

- Production readiness assessment: identifying reliability gaps and incomplete critical paths (several hook files are empty, QA pipeline lacks implementation, snapshot modules lack content).
- Web research on user pain points: how teams currently handle Claude Code session exhaustion, what reliability issues exist in long-running AI coding sessions, and what competing solutions exist in the market.
- Session card UI: deciding whether to display git remote or directory name in card top-right, and generating Discord update messages with sample session card images.
- Test verification: checking test status from last Bash output and fixing any failures.

## Key Decisions Made

- State persistence via git: all session state (tasks, decisions, progress) is stored in version control to enable developer handoffs and audit trails.
- Hook-based integration: Askr injects into Claude Code at five lifecycle points (session start, user prompt submit, session stop, pre-compact, and resumption) rather than wrapping the entire session.