Last updated: 2026-06-10 16:54

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or API quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state (tasks, decisions, progress) and orchestrating safe resumption without losing work or context.

## What's In Flight

- Session report card display: project name, user message count, and API exchange count now render with proper formatting across all checkpoint triggers (context exhaustion, quota exhaustion, session end).
- Daemon restart detection: preventing stale code execution after daemon restarts.
- Auto-continue verification: confirming the auto-continue switch fires correctly in the askr repo after daemon trigger.
- Test suite validation: verifying all tests pass after recent changes to cost.py, report_image.py, stop.py, and checkpoint.py.

## Key Decisions Made

- State persists in git as append-only decision log and task/progress files, enabling handoffs without database dependencies.
- Session monitoring uses token forecasting to predict which limit (context or quota) hits first, triggering checkpoint before exhaustion.
- Safe pause validation ensures interruption only occurs at safe points in the development workflow.
- Report card displays user turns as "N messages (M exchanges)" format to distinguish user prompts from total API calls