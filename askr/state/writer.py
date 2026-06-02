# Phase 1 — State File Writer
#
# Writes and updates the askr state files on every checkpoint and hook event.
#
# Files managed:
#   handover_<developer>.md   — primary session resume file, per developer
#   current_task_<dev>.md     — active objective, per developer
#   implementation_state.md   — progress sections per developer
#   decisions.md              — append-only log (timestamped, never conflicts)
#   architecture.md           — shared system design
#   blockers.md               — known issues and blockers
#
# Design principle: all files are conflict-resistant.
# decisions.md is append-only — two simultaneous writers never conflict.
# per-developer files never conflict by definition.
