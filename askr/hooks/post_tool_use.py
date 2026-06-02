# Claude Code Hook — PostToolUse
#
# Fires after every tool execution.
#
# Actions:
#   - Update implementation_state.md (files modified, commands run, tests executed)
#   - Extract token cost from tool_response.usage for quota burn tracking
#   - Feed to session monitor for live forecast update
