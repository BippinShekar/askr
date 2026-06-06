Last updated: 2026-06-06 18:08

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, so anyone can resume work without losing context.

## What's In Flight

- Integration tests for all 4 stages (7-10) of the CI pipeline; Stage 10 tests project brief generation end-to-end with real checkpoints.
- Secret scrubbing in session transcripts before Claude Haiku processes them (Discord webhooks, API keys, Bearer tokens, random strings).
- Discord webhook setup documentation and `askr report` command in README.
- Verification of test status from latest Bash output and fixing any failures.

## Key Decisions Made

- State is append-only and persisted to git: decisions.md, handover.md, and task files are never edited, only appended. This creates an audit trail and enables safe resumption.
- Session lifecycle is split into four stages: monitor (detect exhaustion), forecast (predict which limit hits first), checkpoint (persist state safely), and resume (inject context on restart).
- Secrets are scrubbed from all transcript text (user messages, assistant responses, Bash commands) before being sent to Claude Ha