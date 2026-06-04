# Architecture

Last updated: 2026-06-04 21:07

## System Overview

Askr is a background daemon that monitors Claude Code sessions via JSONL transcripts and automatically checkpoints work before context/quota limits are exceeded. It persists session state to git and injects project context on session resumption to maintain continuity across developer handoffs.

## Modules

- **cli/** — Entry points for the askr CLI (`ask.py` for Q&A, `askr.py` for hook management)
- **session/** — Core orchestration: `monitor.py` tracks token usage, `forecast.py` predicts which limit hits first, `checkpoint.py` saves state, `lifecycle.py` manages resumption triggers, `safe_pause.py` validates interrupt safety
- **hooks/** — Claude Code integration points: `session_start.py` injects context on resume, `user_prompt_submit.py` extracts active objectives, `stop.py` generates handover docs on session end, `pre_compact.py` emergency checkpoint before auto-compact
- **state/** — Persistence layer: `reader.py` loads developer context from files, `writer.py` saves state/tasks/decisions, `config.py` manages state configuration
- **clients/** — API wrappers: `claude.py` for Anthropic API, `openai.py` for OpenAI API
- **
