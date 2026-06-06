Last updated: 2026-06-06 18:15

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by persisting objectives, decisions, and progress in version control, solving the problem of losing work and context when AI coding sessions hit resource limits.

## What's In Flight

- Integration test suite for all 4 stages of checkpoint/resumption lifecycle (stages 7-10). Currently 7-10 tests needed in CI pipeline.
- End-to-end test of Stage 10 (project brief generation) using real checkpoint data.
- Verification and fix of any test failures from recent Bash output.
- Review of files changed since last session and audit of decisions.md.

## Key Decisions Made

- Do not build a marketing website yet. Installation story is too rough (hardcoded paths, manual venv setup, no package manager support). Website would send users to a product that cannot onboard them effectively.
- Secrets scrubbing implemented in checkpoint.py to prevent credential leaks in git history.
- Discord webhook integration working; credentials stored in .env (gitignored, local only). New webhook created after previous URL exposure.
- State persistence uses append-only decision log and handover documents committed to git for developer continuity.