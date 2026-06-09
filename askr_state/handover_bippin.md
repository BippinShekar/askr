# Handover: bippin

Last updated: 2026-06-10 02:30

# Handover Document

## Task
Investigated how to persist user behavior patterns and command preferences across Claude Code sessions without manual setup, and evaluated whether askr should implement automatic behavior persistence.

## Status
- Researched whether CLAUDE.md is the correct mechanism for persisting session behaviors (confirmed: yes, `~/.claude/CLAUDE.md` loads automatically in every session)
- Identified that askr's session lifecycle system (hooks in `askr/session/lifecycle.py` and `askr/hooks/stop.py`) is not the right layer for behavior persistence
- Confirmed that `~/.claude/CLAUDE.md` already works as a global, automatic persistence mechanism across all projects and sessions
- Conducted web search to determine if other users face this problem and whether existing solutions exist (search completed but results not yet analyzed in transcript)
- Determined that askr *could* add `~/.config/askr/session_behaviors.md` as a future feature for project-specific behavior rules layered on top of global CLAUDE.md

## Failed Approaches
- Using askr's memory/handover system to persist user behavior patterns — rejected because CLAUDE.md already solves this at the OS level and is automatically loaded by every Claude Code session
- Storing behavior rules in askr's session lifecycle hooks — rejected because this couples user preferences to the orchestration layer rather
