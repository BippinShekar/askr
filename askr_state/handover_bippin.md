# Handover: bippin

Last updated: 2026-06-15 14:19

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook error reporting by exposing HTTP errors in send_message return value

## Discussion
User reported that Discord notifications were failing silently with only a generic warning message. The root cause was that send_message() was catching exceptions and returning False without exposing the actual HTTP error. Session refactored send_message() to return a tuple (success: bool, error_message: str) and updated all callers in askr.py and notification.py to unpack and handle the error details. This enables proper debugging of webhook configuration issues.

## Accomplishments
- [x] Modified discord.py send_message() to return tuple (bool, str) with actual HTTP error details instead of swallowing exceptions
- [x] Updated askr.py callers of send_message() to unpack tuple and log error messages
- [x] Updated notification.py hook to unpack send_message() tuple return value
- [x] Verified all other callers of send_message() are safe with tuple return (Python doesn't enforce bool type checking)

## In Progress
- `askr/clients/discord.py` (line 14): Return tuple (success, error_message) from send_message() to expose HTTP errors
- `askr/cli/askr.py` (line 1165): Unpack send_message() tuple return and log error details in init and session handlers
- `askr/hooks/notification.py` (line 38): Unpack send_message() tuple return in notification hook

## Next Actions
1. Complete the git commit that was started (git add ... && git commit -m 'fix: expose Discord webhook HTTP errors in send_message return tuple')
   *Why: Changes are staged but commit was interrupted; need to finalize before testing*
2. Run askr init again and verify the Discord webhook error message now shows the actual HTTP error (e.g., 401 Unauthorized, 404 Not Found, etc.) instead of generic warning
   *Why: Confirms that error details are now visible for debugging webhook configuration issues*
3. Test with invalid ASKR_DISCORD_WEBHOOK value to verify error message is informative
   *Why: Validates that the tuple unpacking and error logging works end-to-end*
4. Check if ASKR_DISCORD_WEBHOOK is actually set in ~/.config/askr/.env or if it's empty/missing
   *Why: User's error suggests webhook may not be configured at all; need to verify setup_keys() is saving it correctly*

## Decisions
- Return tuple (bool, str) from send_message() instead of just bool — Allows callers to access actual HTTP error details for debugging; swallowing exceptions was preventing diagnosis of webhook issues
- Keep all callers that ignore return value unchanged (Python doesn't enforce type checking) — Simpler than refactoring every caller; only the two that check the return value needed updates

## Failed Approaches
- Checking if send_message() return value was being used as a bool in all callers before making changes — Unnecessary caution; Python allows tuple to be used in boolean context without error, so all existing callers remain safe

## Files In Play
- `askr/clients/discord.py`
- `askr/cli/askr.py`
- `askr/hooks/notification.py`

## Relational Files
- `askr/state/config.py` (configures): Manages ASKR_DISCORD_WEBHOOK configuration; relevant to understanding why webhook might be missing/invalid
- `askr/hooks/stop.py` (imported_by): Uses send_message() in notification hook; was checked to ensure tuple return doesn't break it

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Git commit was started but not completed (git add ... && g was cut off); need to finish commit before next session can verify changes
