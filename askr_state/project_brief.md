Last updated: 2026-06-13 21:33

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with LLM integration, persistent state management, and multi-client support. It bridges code editors, LLM APIs, and subprocess execution to enable AI-assisted development workflows with full session history and handover capabilities.

## What's In Flight

- Phase 3.11 completion: post-tool-use hook for extracting and persisting handover deltas from Write/Edit operations. Core files (post_tool_use.py, writer.py, reader.py, checkpoint.py) implemented and committed. Status: 95% complete pending integration testing.
- Phase 3.12 readiness: handover validation and schema enforcement queued for next phase.
- Open: tabular analysis of handover system gaps — unclear if completed this session or remains pending.

## Key Decisions Made

- Handover state persists to JSON via writer.py/reader.py rather than in-memory only — enables cross-session continuity and debugging.
- Post-tool-use hook intercepts Write/Edit operations to extract delta content — keeps handover payload minimal and focused on actual changes.
- Checkpoint.py handles both dict and str goal formats for backward compatibility — avoids breaking existing session state while supporting new JSON-serialized format.
- Session lifecycle managed through usage_api.py as primary