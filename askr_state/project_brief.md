Last updated: 2026-06-13 22:24

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting autonomous continuation. It orchestrates subprocess execution, code analysis, and multi-turn conversations with Claude, allowing developers to hand off work mid-session and resume with full context recovery.

## What's In Flight

- Diagnosing and fixing stale handover file generation: checkpoint writes are occurring before session actions complete, causing autonomous sessions to inherit outdated goals and context. Root cause is premature persistence mid-session rather than after final Claude response and tool execution completion.
- Verifying context checkpoint cards display correct "turns remaining" calculation in staging environment before pushing fixes to main.
- Implementing session-end barrier to defer all checkpoint writes until after final Claude response and pending tool executions are fully resolved.
- Adding validation layer to handover creation to cross-check inferred goals against actual user messages and Claude responses before persistence.

## Key Decisions Made

- Checkpoint and handover files (checkpoint_pending.json, launch_mode.json) are primary state carriers for autonomous session continuation; git diffs alone are insufficient for proper handover.
- Delta extraction happens at the hook level (post_tool_use.py) rather than in checkpoint.py to separate concerns: hooks capture raw deltas, checkpoint orchestrates persistence.
- Backward compatibility maintained for