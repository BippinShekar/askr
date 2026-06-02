# Phase 1 — Discord Notification Engine
#
# Sends structured webhook messages to a configured Discord channel.
#
# Events:
#   - Checkpoint complete (Trigger A or B, what was done, what's next)
#   - Session resumed (after quota reset)
#   - Feature complete
#   - Morning report (sessions overnight, time saved, decisions made)
#   - Weekly summary
#
# Config: DISCORD_WEBHOOK_URL in ~/.config/askr/.env
# Format: clean embeds, no noise, actionable content only.
