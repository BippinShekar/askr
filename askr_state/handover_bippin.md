# Handover: bippin

Last updated: 2026-06-11 13:06

# HANDOVER DOCUMENT

## Task
Implement automatic handover mechanism for Claude Code sessions in the askr extension: capture checkpoint results with prompts, thread handover file paths through the notification system, and auto-load handover files with @file syntax in new sessions.

## Status
Implementation complete across 3 files:

- **lifecycle.py**: Removed timeout/deadline logic. Added `handover_path` threading through `_execute_trigger`, `_wait_for_stop_hook_or_fallback`, and `_start_claude`. Modified `_start_claude` to auto-detect handover file in session directory and inject `@file <path>` into prompt. Modified `_wait_for_stop_hook_or_fallback` to capture checkpoint result and add `prompt` field to context notification.

- **stop.py** (`_handle_pending_checkpoint`): Now captures checkpoint result and adds `prompt` field to notification payload before sending context notification.

- **extension.js**: Updated to read `n.prompt` from incoming notifications and use it as the initial prompt text when launching Claude.

All edits applied. No syntax errors detected in final grep verification.

## Failed Approaches
None.

## Next Action
Run the askr extension end-to-end: trigger a session, let it reach checkpoint/stop hook, verify the handover file
