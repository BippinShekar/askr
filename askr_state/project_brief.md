Last updated: 2026-06-06 21:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context and decision history, turning long-running coding tasks into resumable workflows.

## What's In Flight

- Guard engine Phase 3.5: async delivery mechanism with IDE popup and Discord notifications, append-only audit logging to guard_log.md. Committed and ready for end-to-end testing.
- Integration test suite: building out 7-10 test cases across all 4 stages of the checkpoint/resumption pipeline for CI.
- Stage 10 project brief generation: validating end-to-end flow with real checkpoint data.

## Key Decisions Made

- State persisted to git with append-only decision log and handover documents. Enables developer handoffs without external databases.
- Guard checks run asynchronously in subprocess to avoid blocking Claude's tool execution. Warnings logged to guard_log.md with timestamp and trigger type.
- Forecast module predicts which limit (context or quota) hits first, allowing proactive checkpoint before exhaustion rather than reactive recovery.
- Hook-based integration with Claude Code: session_start, user_prompt_submit, stop, pre_compact, pre_tool_