Last updated: 2026-06-11 22:20

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It then orchestrates resumption in a fresh session with full context restored. The core problem: Claude Code sessions hit token limits mid-task, losing context and forcing manual recovery. Askr makes this seamless by treating sessions as resumable units.

## What's In Flight

- Extension fix validation: stdin-based prompt delivery (instead of command-line args) to work around Claude initialization timing. Currently at 52% context, deliberately burning tokens to reach 65% threshold where autonomous trigger fires.
- Session monitoring and forecasting: predicting which limit (context or quota) hits first, with ~23-minute window before autonomous trigger in current session.
- State persistence: task/decision/progress tracking across session boundaries via git commits.

## Key Decisions Made

- Append-only decision log in decisions.md; never edit existing lines, only add new ones.
- State stored in git to enable developer handoffs and session resumption without manual context reconstruction.
- Daemon triggers autonomous session at 65% context threshold; extension receives prompt via stdin after 4-second initialization wait.
- Safe pause validation required before checkpoint to avoid interrupting mid-operation.
- Two extension locations maintained: source