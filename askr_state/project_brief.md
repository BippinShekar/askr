Last updated: 2026-06-06 23:12

# Project Brief

Askr is a daemon and CLI tool that solves context loss and flow interruption when developers pause Claude Code sessions. It monitors token usage, detects when context or quota limits are about to be exhausted, automatically checkpoints project state to git, and enables seamless resumption in new sessions. The core problem: Claude gets you productive, but switching tools or pausing mid-thought breaks flow and loses your train of thought. Askr keeps your context alive across session boundaries.

## What's In Flight

- Social media launch campaign: drafting Twitter/X post framing the problem statement (context loss on tool switching) before public launch. No draft exists yet; waiting on tone/positioning decisions.
- Test suite verification: checking status from last Bash output and fixing any failures.
- Session state handover: reviewing files changed since last session and validating decisions.md consistency.

## Key Decisions Made

- Append-only decision log: all decisions timestamped and reasoned; never edited retroactively. Ensures audit trail and prevents context loss between handoffs.
- Git as source of truth for project state: checkpoints persist tasks, decisions, and progress to version control, enabling developer handoffs without external databases.
- Hook-based integration with Claude Code: session lifecycle is managed through five integration points (start, prompt submit, stop, pre-compact, resume) rather than monkey-