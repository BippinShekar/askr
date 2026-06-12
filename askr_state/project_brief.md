Last updated: 2026-06-12 19:01

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before the session breaks. It then orchestrates resumption in a fresh session with full context restored. The core problem: Claude Code sessions have hard limits, and hitting them mid-task loses work and context. Askr makes those limits invisible to developers.

## What's In Flight

- Goal state management fix: completed goals are being resurrected as active in new sessions. Root cause identified in `_get_next_goal()` logic — it's not filtering by completion status. Currently tracing goals.md completion marker format and filtering logic.
- Discord notification gating: verifying that `_start_claude` boolean return properly gates notification sends.
- macOS Terminal.app keystroke fallback: testing actual Claude launch via keystroke injection as fallback to direct API.
- Session card UI: deciding whether to display git remote or directory name in top-right; generating sample Discord update message with card image.
- Test suite validation: verifying all tests pass after recent goal state changes.

## Key Decisions Made

- Goal passed as context, not directive: stale stored goals no longer override handover's Next Action. Goal context is injected for reference, not treated as active work assignment.
- Prompt delay set