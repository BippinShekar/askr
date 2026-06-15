Last updated: 2026-06-16 04:00

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive sessions with an LLM, analyzes code, generates solutions, and hands off work to autonomous continuation. It integrates with IDEs, manages session state across restarts, and notifies users of progress. The core problem: developers need an AI agent that understands project context, persists work across sessions, and can resume autonomously without losing intent.

## What's In Flight

- Multi-user sync mechanism: resolving race conditions when two co-founders push state files simultaneously. Current blocker to adoption.
- Handover system redesign: root cause identified (stop checkpoint handler never invoked); requires architectural fix to defer goal inference until session-end validation.
- On-demand project_brief.md generation: implementing git post-pull hook to generate this file in-memory rather than committing it, eliminating merge conflicts.
- Architecture.md elevation: refactoring to become the single comprehensive tracking artifact for all project phases, replacing fragmented state files.
- Two-user workflow validation: testing parallel askr sessions between co-founders to confirm sync conflicts are resolved.

## Key Decisions Made

- Handover creation is not a race condition—it's a logic gap. The stop checkpoint handler is never invoked, so stale checkpoints are a symptom of missing handler logic, not timing issues.
- Goal