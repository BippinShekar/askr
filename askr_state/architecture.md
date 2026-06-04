# Architecture

Last updated: 2026-06-05 01:30

## System Overview

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects context/quota exhaustion, and orchestrates automatic checkpoints and resumption. It maintains project state in git to enable handoffs between developers and sessions.

## Modules

- **`askr/session/`** — Session lifecycle management: `monitor.py` tracks token usage, `forecast.py` predicts which limit (context or quota) will be hit first, `checkpoint.py` persists state before exhaustion, `lifecycle.py` triggers resumption, `safe_pause.py` validates safe interruption points.

- **`askr/hooks/`** — Claude Code integration points: `session_start.py` injects context on session begin, `user_prompt_submit.py` extracts and stores active objectives, `stop.py` generates handover docs and commits state on session end, `pre_compact.py` emergency checkpoint before context auto-compaction.

- **`askr/state/`** — Persistent state layer: `reader.py` loads developer context from state files, `writer.py` manages state file updates for tasks/decisions/progress, `config.py` state configuration.

- **`askr/qa/`** — Code analysis: `context_loader.py` loads project context and snapshots, `graph
