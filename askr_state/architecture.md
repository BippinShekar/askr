# Architecture

Last updated: 2026-06-02 17:56

# Architecture

## System Overview

Askr monitors Claude Code sessions to prevent context exhaustion and quota limits from interrupting work. It checkpoints session state before Claude degrades, resumes automatically, and syncs project state to git for team continuity.

## Modules

- **cli/** - Command-line interface. `ask.py` provides code Q&A against project codebases. `askr.py` manages hook installation and configuration.
- **session/** - Session lifecycle management. `monitor.py` tracks token usage from two sources. `forecast.py` predicts which limit (context or quota) will be exceeded first. `checkpoint.py` persists state and creates handover documents. `lifecycle.py` manages resumption triggers. `safe_pause.py` validates system state before interrupting.
- **hooks/** - Claude Code lifecycle hooks. `session_start.py` initializes sessions with git state and context. `stop.py` generates handover docs and commits state on session end. `user_prompt_submit.py` extracts and stores active objectives. `pre_compact.py` emergency checkpoint before Claude auto-compacts.
- **state/** - Persistent state management. `reader.py` loads developer context from state files. `writer.py` manages handover documents, task tracking, and progress files. `config.py` state configuration.
-
