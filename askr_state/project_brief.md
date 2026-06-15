Last updated: 2026-06-15 13:50

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persists state across runs, and integrates with IDEs and external services like Discord. It orchestrates subprocess execution, manages session lifecycle, and provides handover capabilities so users can pause and resume work across multiple invocations.

## What's In Flight

- Discord webhook prompt visibility during `askr init` — currently using `getpass()` which hides input; needs verification in staging and possible switch to `input()` for better UX
- Checkpoint card display validation — verifying that 'turns remaining' calculation displays correctly in staging before merging report_image.py fixes
- Handover system architectural redesign — current checkpoint timing creates stale goals; requires rework of when goal inference happens (session-end validation, not mid-session auto-inference)
- Goal inference refactoring — shifting from message-aware to session-aware inference to prevent autonomous sessions from inheriting outdated objectives

## Key Decisions Made

- Treat `checkpoint_pending.json` and `launch_mode.json` as primary handover state carriers, not git diffs alone — investigation showed these files control autonomous continuation
- Handle both dict and str goal formats in checkpoint.py for backward compatibility while supporting new JSON-serialized format
- Defer goal inference until session-end validation rather than auto