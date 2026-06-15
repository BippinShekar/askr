Last updated: 2026-06-15 14:31

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, tracks state across executions, and integrates with external services (Discord webhooks, IDE adapters, code analysis clients) to provide real-time feedback and notifications. It solves the problem of maintaining context and continuity in multi-turn AI-assisted coding workflows, especially when handing off work between sessions or team members.

## What's In Flight

- Per-repo webhook configuration system: currently all Discord webhooks are stored globally in ~/.config/askr/.env; user needs ability to use different webhooks for private vs. official projects. Decision pending on whether to use repo-level .env overrides, environment variables, or Phase 4 team/project scoping.
- macOS SSL certificate verification fix: applied certifi library to discord.py send_message and send_file methods; awaiting verification that friend's SSL error is resolved.
- Context checkpoint card display: verifying that 'turns remaining' calculation displays correctly in staging before pushing report_image.py fixes to main.

## Key Decisions Made

- Handover system requires architectural redesign, not incremental fixes: stale checkpoints are a fundamental timing issue where the stop checkpoint handler is never invoked, not a data formatting problem.
- Goal inference must be session-aware and deferred until session-end validation: