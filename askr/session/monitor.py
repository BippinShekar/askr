# Phase 1  - Session Monitor
#
# Watches two data sources simultaneously:
#   1. ~/.claude/projects/<project>/<session>.jsonl  - token usage per turn
#   2. StatusLine JSON payload  - remaining_percentage live from Claude Code
#
# Feeds burn rates to forecast.py on every turn.
