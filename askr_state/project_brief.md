Last updated: 2026-06-12 19:27

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in structured state files that Claude can read on resumption.

## What's In Flight

- Implementation guard mechanism analysis: diagnosing why the current guard fails to prevent Claude from suggesting contradictory changes that break the codebase. Requires tabular failure-mode analysis and concrete improvements with tradeoffs.
- Goal completion flow: refactored this session to integrate completed goals into handover generation via Haiku analysis of session transcript, with checkpoint parsing and goals.md updates before next session starts.
- Discord notification gating: verify that _start_claude boolean return properly gates notifications; Terminal.app keystroke fallback testing on macOS with actual Claude launch.
- Session card display: decide whether to show git remote or directory name in card top-right; generate sample Discord update message with session card image.

## Key Decisions Made

- Checkpoint max_tokens increased from 300 to 2000 to accommodate expanded handover with completed goals section.
- Goal completion moved from file-heuristic inference to handover-integrated Haiku analysis: Claude identifies completed goals in transcript, checkpoint par