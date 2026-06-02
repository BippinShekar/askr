# Claude Code Hook — UserPromptSubmit
#
# Fires on every user message before Claude responds.
#
# Actions:
#   - Parse intent from prompt
#   - Update current_task.md with active objective
#   - Feed turn metadata to session monitor (token count, timestamp)
