Last updated: 2026-06-06 18:32

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git. It enables seamless handoffs between developers and sessions by maintaining persistent context, decisions, and progress in version control. The core problem: Claude Code sessions end abruptly when limits hit, losing work and context. Askr prevents that.

## What's In Flight

- Phase 3.5 implementation in committed stages with integration tests for all 4 checkpoint/resumption stages (7-10) in CI pipeline
- End-to-end test of Stage 10 project brief generation with real checkpoint data
- Twitter/open-source positioning strategy and messaging
- Pre-implementation briefing for next phase
- Secrets scrubbing already shipped: Discord webhooks, API keys (sk-ant-, sk-proj-, sk-), Bearer tokens, and random strings are stripped before reaching Haiku on every message

## Key Decisions Made

- Secrets scrubbing runs on every user message, assistant text, and Bash command output to prevent accidental leaks
- Do not build marketing website yet; product onboarding (hardcoded paths, venv setup, no brew install) must be cleaned first before conversion-focused marketing
- No direct competitors exist; individual features have analogs elsewhere but no tool