Last updated: 2026-06-12 20:19

# Project Brief

Askr is a CLI-based AI coding agent that runs interactive development sessions with an LLM backend, persistent state management, and multi-client support. It bridges code editors, subprocess execution, and AI services to enable developers to work with an AI assistant that understands project context across sessions.

## What's In Flight

- Three-stage checkpoint workflow: guard installation into CLAUDE.md, architecture.md regeneration, and continuous integration validation. All stages are wired and functional; end-to-end testing is underway to confirm no regressions.
- State persistence layer: session state serialized to ./askr_state/ directory; recovery and cross-invocation consistency being validated.
- LLM client abstraction: multi-provider support (OpenAI, Anthropic) via ./askr/clients/; request/response formatting standardized.

## Key Decisions Made

- Entry point is usage_api.py in ./askr/session/; all session initialization and subprocess orchestration flows through this module.
- State schema lives in ./askr/state/; any changes here cascade across all modules that depend on session recovery.
- Hooks system (./askr/hooks/) decouples lifecycle events from core logic; pre/post session and execution handlers are extensible.
- IDE integration (./askr/ide/) owns file operations and editor bridging