# Handover: bippin

Last updated: 2026-06-10 11:40

# Handover: askr Status Bar Context % Display Fix

## Task
Fix the askr VS Code extension status bar to display accurate context percentage for the current workspace, eliminating stale data from other projects bleeding into the display.

## Status
- **Root cause identified**: Extension reads `session_stats.json` without validating that `project_path` matches the current VS Code workspace. Stale stats from other projects persist in the display until a new message is sent in the current project.
- **SessionStart hook** (`/Users/bippin/Desktop/askr/askr/hooks/session_start.py`): Modified to write a blank stats entry with `ctx: 0%` for the current project immediately when a session starts, before any user message is sent.
- **Extension** (`/Users/bippin/.cursor/extensions/askr.askr-status-1.0.0/extension.js`): Needs modification to validate `session_stats.project_path` against current VS Code workspace root before displaying stats. If project_path does not match current workspace, display should show `ctx:0%` or "no session" state.
- **Stats file location**: `/Users/bippin/.config/askr/session_stats.json` — contains `project_path`, `ctx_used`, and other fields.
- **Backup of
