# Handover: bippin

Last updated: 2026-06-06 13:50

## Task
Fix goal lifecycle management in askr: auto-archive stale goals at session start and remove stale goals from continuation prompts to prevent adoption friction from manual goal management.

## Status
- askr/state/goals.py — `archive_stale_goals()` function implemented, moves uncompleted goals from past-dated sections to backlog
- askr/hooks/session_start.py — modified to call `archive_stale_goals()` before goal suggestion logic
- askr/ide/vscode-extension/extension.js — stale goal removed from continuation prompt
- askr/.cursor/extensions/askr.askr-status-1.0.0/extension.js — stale goal removed from continuation prompt
- askr_state/goals.md — two stale goals ("Verify test status", one other) already archived to backlog via manual execution of `archive_stale_goals()`
- Changes committed and pushed to git

## Failed Approaches
None

## Next Action
Run the full test suite to verify that session_start.py correctly triggers goal archival on next session initialization and that the extension loads without errors. Command: `source venv/bin/activate && python3 -m pytest askr/hooks/test_session_start.py -v`

## Open Questions
- Whether goal inference logic in session_
