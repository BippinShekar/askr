Last updated: 2026-06-10 11:29

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are approaching exhaustion, and automatically checkpoints project state to git before those limits are hit. It enables seamless handoffs between developers and sessions by maintaining persistent state—active objectives, decisions, progress—so anyone can resume work without losing context.

## What's In Flight

- Fixing goal notification UX in the Cursor extension: currently displays "goals stale 6h+" without showing actual goal text, making it impossible for users to decide what to keep or discard during context exhaustion.
- Resolving auto-compact trigger mismatch: Claude Code fires auto-compact at ~43% context, but askr's daemon threshold is set to 65%, creating a gap where Claude compacts before askr can checkpoint.
- Verifying quota percentage semantics: confirmed that `quota:5%` means 5% USED (95% remaining), but need to audit all UI and docs for consistency.

## Key Decisions Made

- State is append-only and stored in git: decisions.md, handover.md, and task files are never edited, only appended. This creates an audit trail and prevents merge conflicts during concurrent sessions.
- Context measurement reads raw token counts from Claude API responses (input_tokens + cache_read_input_tokens + cache_creation_