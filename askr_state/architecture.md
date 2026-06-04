# Architecture

Last updated: 2026-06-04 19:36

## System Overview

Askr monitors Claude Code sessions to prevent context exhaustion and quota limits from interrupting work. It checkpoints session state before Claude degrades, resumes automatically, and syncs project state to git for team continuity.

## Modules

- **cli/** - Command-line interface. `ask.py` provides a code Q&A system; `askr.py` manages hook installation and configuration.
- **session/** - Session lifecycle management. `forecast.py` predicts token burn rates; `monitor.py` tracks real-time usage; `checkpoint.py` persists state; `lifecycle.py` handles resumption; `safe_pause.py` validates interruption safety.
- **hooks/** - Claude Code lifecycle hooks. `pre_compact.py` checkpoints before auto-compaction; `stop.py` generates handover docs and commits state; `session_start.py` injects context on startup; `user_prompt_submit.py` extracts active objectives.
- **state/** - Persistent state management. `reader.py` loads developer context from files; `writer.py` manages handover and task state files; `config.py` handles state configuration.
- **qa/** - Code analysis for context injection. `context_loader.py` loads project context; `graph.py` extracts import dependencies; `modes
