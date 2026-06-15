Last updated: 2026-06-15 18:28

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across runs and supporting autonomous continuation. It solves the problem of maintaining context and intent across fragmented coding workflows—allowing users to have research conversations, make implementation decisions, and hand off work to autonomous execution without losing the thread.

## What's In Flight

- Direction proposal flow: talk-only sessions (research/discussion) now surface for user approval before autonomous execution, replacing silent skip logic with three-button UI (Approve/Reject/Edit) in VS Code
- End-to-end validation of direction proposal: testing all three button paths and Signal 3 fallback logic to ensure autonomous runs use correct direction
- Commit and merge of lifecycle.py, stop.py, and extension.js changes
- Update implementation_state.md to reflect completion status

## Key Decisions Made

- Talk-only sessions return proposed=True instead of being silently skipped—preserves user intent from research conclusions while maintaining explicit approval gate for autonomous execution
- Three-button UI (Approve/Reject/Edit) instead of auto-executing on proposal—user retains full control; prevents autonomous runs from misinterpreting research discussions as implementation directives
- Signal 3 walks session history to find fallback coding session if proposal is rejected—ensures autonomous execution always has valid direction even