Last updated: 2026-06-14 14:34

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with LLM integration, state persistence, and multi-client support. It allows users to collaborate with AI on code generation and modification, with the ability to hand off sessions to other users or autonomous continuation. The core problem it solves is enabling seamless, stateful AI-assisted development workflows that persist across sessions and team members.

## What's In Flight

- Handover system redesign: fixing stale checkpoint creation that prevents proper session continuation. Root cause identified as missing stop checkpoint handler invocation; requires architectural fix, not incremental patching.
- Goal inference timing: deferring auto-inferred goals from session-start to session-end validation to prevent stale objectives from poisoning autonomous handovers.
- Collaboration feature roadmap: disaggregating three bundled requests (remote session control, task injection, auto-run) and determining phase placement with permission-based safety constraints.
- Approval gate system design: mapping dangerous permissions (skip, file deletion, env modification) to required approval triggers, with explicit focus on preventing permission compounding across sessions.
- Context checkpoint card verification: staging validation of 'turns remaining' display before pushing report_image.py fixes to main.

## Key Decisions Made

- Checkpoint state carriers (checkpoint_pending.json, launch_mode.json) are