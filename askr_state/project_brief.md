Last updated: 2026-06-06 23:15

# Project Brief

Askr is a daemon and CLI tool that solves context loss during Claude Code sessions. When Claude hits context limits or quota resets, the developer's train of thought and progress vanish. Askr monitors token usage, predicts exhaustion, automatically checkpoints project state to git, and orchestrates seamless resumption—enabling developers to pause and hand off work without losing context or momentum.

## What's In Flight

- Twitter/X problem validation post: drafting a concise, sub-280-character statement of the core problem (Claude pauses → context/flow lost) without product positioning. Goal is to validate the problem with followers before pitching a solution.
- Test suite verification: checking Bash output from last session for failures and fixing any broken tests.
- State file review: auditing files changed since last session and cross-referencing against decisions.md.

## Key Decisions Made

- Append-only decision log: all decisions timestamped and reasoned; never edited or deleted. Ensures full audit trail and prevents revisionist history.
- Git-backed state persistence: project state (tasks, decisions, progress) stored in version control to enable developer handoffs and session resumption without manual context transfer.
- Problem-first messaging: Twitter validation focuses on the problem statement only (context loss on pause), not the product or solution. Avoids premature positioning.
-