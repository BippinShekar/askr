Last updated: 2026-06-12 01:50

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent task context, decisions, and progress in version control.

## What's In Flight

- Claude session resumption flow: `_start_claude` now returns boolean; Discord notifications gated on successful start; Terminal.app fallback replaced with two-step keystroke script for proper CR submission (lifecycle.py completed, extension.js CR/LF fix committed).
- Discord notification card generation: sample session card image with git remote/directory name display pending decision.
- macOS keystroke fallback validation: Terminal.app launch + osascript CR submission needs real-world testing against actual Claude startup.
- Test suite verification: last Bash output status needs review and any failures fixed.

## Key Decisions Made

- State persisted to git as append-only decision log and task/progress files; enables full context recovery across sessions and developers.
- Forecast module predicts which limit (context or quota) hits first; checkpoint triggered before exhaustion, not after.
- Session hooks injected at four points: start (context injection), prompt submit (objective capture), stop (handover doc generation), pre-compact (emergency checkpoint).
-