Last updated: 2026-06-12 19:05

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or token quota is about to exhaust, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining a persistent record of objectives, decisions, and progress in version control.

## What's In Flight

- Goal completion detection: integrating completion inference into handover generation itself (pass open goals to Haiku, parse results back into goals.md). Staged changes in checkpoint.py and claude.py; git commit message incomplete.
- Discord notification gating: verifying _start_claude boolean return properly gates notifications.
- macOS Terminal.app keystroke fallback: testing actual Claude launch with Terminal.app on macOS.
- Handover card UI: deciding whether to display git remote or directory name in top-right; generating sample Discord update message with session card image.

## Key Decisions Made

- Goal completion detection belongs in handover generation, not as separate file-heuristic analysis. Haiku prompt identifies completed goals from session transcript; results parsed back into goals.md. This prevents sync drift between user accomplishment and system records.
- Checkpoint token budget raised from 300 to 2000 tokens to accommodate goal completion section in handover text.
- State persisted as append-only git commits with structured handover