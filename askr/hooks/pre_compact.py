# Claude Code Hook  - PreCompact
#
# Emergency fallback  - fires when Claude is about to auto-compact.
# Askr should act well before this via forecast.py (~90% threshold).
# If this fires, something was missed.
#
# Actions:
#   - Generate emergency handover.md
#   - Update state files with whatever context is available
#   - Log that forecast missed the threshold (for calibration)
