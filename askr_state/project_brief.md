Last updated: 2026-06-13 03:10

# Project Brief

Askr is a CLI-based AI coding agent that manages interactive development sessions with LLM integration, state persistence, and multi-client support. It orchestrates AI-assisted coding workflows through subprocess execution, maintains session state across invocations, and integrates with IDEs and multiple LLM providers.

## What's In Flight

- Stress-test readiness analysis: identifying and documenting 3-5 critical blockers in handover system and state management
- Handover system implementation: transcript management and checkpoint persistence between sessions
- Investigation of transcript limits (_MAX_TRANSCRIPT_ENTRIES) and potential data loss during stress tests
- Tabular analysis of handover system gaps with evidence from examined files and state readers/writers

## Key Decisions Made

- Session orchestration routed through `usage_api.py` with platform-aware subprocess execution for cross-OS compatibility
- Filesystem-based state persistence in `./askr_state/` directory rather than database backend for simplicity and portability
- Multi-client abstraction layer in `./askr/clients/` to support multiple LLM providers without coupling to specific implementations
- Lifecycle hooks system (`./askr/hooks/`) for extensibility rather than monolithic session logic
- Append-only decision log to maintain audit trail of architectural choices

## Open Goals

- Complete grep analysis of transcript path