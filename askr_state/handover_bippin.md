# Handover: bippin

Last updated: 2026-06-05 12:15

## Task
Understand how askr (a token/quota tracking system for Claude Code sessions) works and determine the optimal way to use Claude to maximize askr's functionality, particularly regarding token bloat prevention and session continuity.

## Status
- /Users/bippin/Desktop/askr/ — Project structure examined. Contains hooks/, session/, state/ subdirectories and README.md
- /Users/bippin/.cursor/extensions/askr.askr-status-1.0.0/extension.js — IDE extension reviewed. Passive status bar that polls session_stats.json every 5s, displays context%, quota%, reset countdown
- /Users/bippin/Desktop/askr/askr/hooks/stop.py — Examined
- /Users/bippin/Desktop/askr/askr/session/checkpoint.py — Examined. Reads last 60 transcript entries, uses Haiku to populate: Task, Status (with file paths), Failed Approaches, Next Action, Open Questions
- /Users/bippin/Desktop/askr/askr/state/reader.py — Examined
- /Users/bippin/Desktop/askr/askr/hooks/post_tool_use.py — Examined
- /Users/bippin/Desktop/askr/askr/state/writer.py — Examined
- Understanding
