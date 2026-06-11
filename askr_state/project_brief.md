Last updated: 2026-06-11 22:17

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. When a limit is hit, it generates handover documentation and can trigger resumption in a fresh session without manual intervention. The core problem: long-running coding tasks in Claude Code hit token limits mid-work, losing context and requiring manual recovery. Askr makes these interruptions invisible to the developer.

## What's In Flight

- Autonomous session continuation: implementing two-phase prompt delivery to Claude Code extension (initialize extension first, then send prompt via stdin) so handover sessions auto-submit without manual user action. Current blocker: extension reload timing and stdin delivery reliability.
- Session state persistence: building out state reader/writer to maintain task context, decisions, and progress across session boundaries in git.
- Token forecasting: predicting which limit (context or quota) will be hit first to trigger checkpoints at the right moment.
- Discord integration: generating update messages with session card images for team visibility.

## Key Decisions Made

- State lives in git, not a database. Enables handoffs between developers and machines, version control, and offline operation.
- Checkpoint before exhaustion, not after. Prevents mid-thought interruptions and lost work.
- Two-phase extension initialization required. Single-phase