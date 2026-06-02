# Claude Code Hook  - SessionStart
#
# Fires at the start of every Claude Code session.
#
# Actions:
#   1. git pull (get latest state from co-founder's last session)
#   2. Read handover.md (own) + co-founder's handover_<name>.md
#   3. Read decisions.md, architecture.md, current_task.md
#   4. Inject all state into session context via stdout
#
# Claude starts every session already knowing what happened last.
