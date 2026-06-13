Last updated: 2026-06-13 21:21

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM, persisting state across invocations and supporting multiple LLM clients. It orchestrates subprocess execution, maintains session context, and integrates with IDEs to provide continuous AI-assisted coding workflows.

## What's In Flight

- Roadmap phases 3.11-3.15 validation and correction for rejection/disagreement tracking in the handover system. Staged changes pending commit to roadmap.md.
- Implementation of rejection/disagreement tracking mechanism in the handover system to prevent Claude from repeating mistakes across session boundaries (documented failure in GitHub issue #37314).
- Stress-test readiness assessment: identifying and documenting critical blockers. Rejection/disagreement tracking gap confirmed as blocker.
- Line number tracking reliability fix: current Haiku-based inference is unreliable; alternative approach needed for accurate last_known_line tracking in transcripts.

## Key Decisions Made

- Session orchestration centralized in usage_api.py; all subprocess management and platform detection flows through this entry point.
- Multi-client abstraction layer (clients/) decouples LLM provider logic from session management, enabling support for multiple providers.
- State persistence uses append-only artifact storage in ./askr_state/ directory; schema changes here cascade to session and