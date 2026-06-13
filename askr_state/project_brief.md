Last updated: 2026-06-13 20:54

# Project Brief

Askr is a CLI-based AI coding agent that executes interactive development sessions with an LLM, persisting state across checkpoints and supporting multi-client workflows. It orchestrates code execution, maintains conversation history, and integrates with IDEs—solving the problem of maintaining coherent AI-assisted development context across long sessions and handoffs.

## What's In Flight

- Emergency handover mechanism redesign: replacing static markdown templates with typed JSON schema that captures mid-operation state, interrupted execution points, pending tasks, and rejected decisions (phases 3.11-3.15 active)
- Stress-test readiness: identifying and documenting 3-5 critical blockers preventing full cycle validation
- Handover system gap analysis: tabular evidence collection from examined file systems and session startup logic
- Recovery mechanism implementation: enabling resume from exact interrupted state rather than session restart

## Key Decisions Made

- Session orchestration centralized in `usage_api.py`; all major flows pass through this single entry point to maintain state consistency
- State management is file-based (JSON in `./askr_state/`) and centralized; clients are stateless to enable clean handoffs
- Hooks enable side effects (notifications, validation) without coupling modules; extensibility without core modification
- Emergency checkpoints require separate schema from regular handover: operation_state, interrupted_at,