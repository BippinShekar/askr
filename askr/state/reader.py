# Phase 1 — State File Reader
#
# Reads state files and formats them for injection into Claude session context.
#
# Used by: hooks/session_start.py
#
# Loads:
#   - Own handover.md
#   - Co-founder handover files (handover_*.md)
#   - decisions.md (last N entries)
#   - architecture.md
#   - current_task files for all developers
#   - blockers.md
#
# Returns structured context string Claude can act on immediately.
