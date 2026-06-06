# Handover: bippin

Last updated: 2026-06-06 14:05

## Task
Implement stale goal detection and user accountability flow: flag goals abandoned >6 hours ago, prompt user to mark as discarded or completed, log outcome.

## Status
- askr/state/goals.py — Added `get_stale_goals()` and `discard_goal()` functions; `load_today_goals()` and `load_open_goals()` strip timestamp comments; `complete_goal()` handles lines with timestamps. Not yet tested.
- askr/hooks/session_start.py — Added stale goal check that triggers `goal_check` event with list of stale goals. Not yet tested.
- askr/ide/vscode-extension/extension.js — Added handler for `goal_check` event. Not yet tested.
- askr/.cursor/extensions/askr.askr-status-1.0.0/extension.js — Added handler for `goal_check` event. Not yet tested.
- askr/cli/askr.py — Added `askr goal discard <goal_id>` command. Not yet tested.
- Git staging: changes to goals.py, session_start.py, both extension files staged but not committed.

## Failed Approaches
None

## Next Action
Run integration test: activate venv, start a new session with at least one goal older
