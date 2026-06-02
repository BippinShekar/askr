# Claude Code Hook  - Stop
#
# Fires when Claude Code session ends (user stops, session interrupted, etc.)
#
# Actions:
#   - Write handover.md with current session state
#   - Update decisions.md, implementation_state.md
#   - Git commit + push
#   - Send notification if Discord webhook configured
#   - Log session metrics (duration, turns, tokens, time saved estimate)
