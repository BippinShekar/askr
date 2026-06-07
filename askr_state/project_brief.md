Last updated: 2026-06-07 08:25

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It then orchestrates session resumption with full context restoration, enabling seamless handoffs between developers and across session boundaries. The core problem: Claude Code sessions die when limits hit, losing work and forcing manual context reconstruction.

## What's In Flight

- Permission inheritance for auto-started sessions: designing mechanism to read parent session permissions from `.claude/settings.json` and serialize them into handover documents so child sessions inherit tool grants without manual re-approval.
- Rich visual Discord reporting (Phase 3.7): generating PNG reports via matplotlib showing token usage and cost savings, sent as file attachments via webhook.
- Test verification and decision review from last session.

## Key Decisions Made

- State persisted to git via handover documents and state files (tasks, decisions, progress) rather than external database—enables offline access and version control.
- Permission model: "always allow" permissions persist across sessions; "allow once" permissions die with session termination. Child sessions must inherit parent permissions explicitly.
- Emergency checkpoint triggered by `pre_compact.py` hook before Claude's automatic context compaction.
- Append-only decision log in decisions.md—never edit existing lines, only append.

##