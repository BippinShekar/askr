Last updated: 2026-06-06 17:53

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It then orchestrates resumption in a fresh session with full context restored. The core problem: Claude Code sessions have hard limits, and losing work mid-task or forcing developers to manually hand off context between sessions wastes time and breaks flow.

## What's In Flight

- Integration test suite for all 4 checkpoint stages (stages 7-10) in CI pipeline. Currently verifying test status and fixing failures from last bash output.
- End-to-end test of Stage 10 (project brief generation) using a real checkpoint to validate handover document completeness.
- Discord webhook delivery: User-Agent header added to resolve Cloudflare 1010 bot detection. Stop hook timeout increased from 15s to 60s to allow handover file generation to complete. `write_handover()` now returns file path instead of None.
- Next action: run full checkpoint cycle to confirm handover generation completes within new timeout and Discord notification fires.

## Key Decisions Made

- State persisted to git, not a database. Enables handoffs between developers and sessions without external infrastructure.
- Four-stage checkpoint flow: forecast exhaustion, safe pause at a valid interruption point