# Handover: bippin

Last updated: 2026-06-05 12:13

## Task
Determine the optimal usage pattern for Claude (IDE extension vs terminal) to maximize askr's functionality and context tracking.

## Status
askr is a dual-interface tool with:
- IDE extension (Cursor) at /Users/bippin/.cursor/extensions/askr.askr-status-1.0.0/ — read-only status bar polling session_stats.json every 5s, displays context%, quota%, reset countdown
- Terminal CLI at /Users/bippin/Desktop/askr/ — active command interface
- Checkpoint system in askr/session/checkpoint.py — reads last 60 transcript entries, uses Haiku to populate Task, Status, Failed Approaches, Next Action, Open Questions sections
- Hook system in askr/hooks/stop.py — captures Claude behavior at session boundaries
- State reader in askr/state/reader.py — parses session state

## Failed Approaches
- Treating IDE extension as active control interface — it is passive read-only only
- Assuming user must manually manage file names and state in handover documents — handover generation should automatically actualize user intent

## Next Action
Clarify with user: does askr's checkpoint system automatically extract task context from Claude conversation transcripts without requiring explicit file/task naming from the user? If yes, document the exact mechanism by which checkpoint.py converts raw transcript
