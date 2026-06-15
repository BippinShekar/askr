# Handover: bippin

Last updated: 2026-06-15 13:06

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook pickup from local .env file and commit/push changes to askr repository

## Discussion
Identified that the global ~/.config/askr/.env was taking precedence over local .env, preventing Discord webhook from being loaded. The fix involved updating env.py to use override=False on local dotenv load, and updating askr.py to call env.load() at startup. Changes were committed and pushed. User clarified that friend only needs to git pull — no need to rerun askr init since env.load() fires on every import.

## Accomplishments
- [x] Identified root cause: global .env override preventing local webhook pickup
- [x] Fixed env.py to use override=False on local .env load
- [x] Fixed askr.py to call env.load() at startup
- [x] Committed and pushed both changes to repository

## Next Actions
1. Inform friend to run 'git pull' in askr clone to get the env.py and askr.py fixes
   *Why: Changes are now pushed and ready to be pulled*
2. Verify friend's local .env has ASKR_DISCORD_WEBHOOK set correctly
   *Why: The fix now allows local .env to be read; webhook must exist in that file*
3. Have friend run any askr command (e.g., 'askr' or 'askr init') to trigger env.load() and pick up webhook
   *Why: env.load() runs on every import, so next command execution will load the webhook automatically*
4. Test that project brief is sent to Discord webhook on next askr session
   *Why: Confirms the webhook is now being picked up and used correctly*

## Decisions
- No need to ask friend to rerun 'askr init' after git pull — env.load() fires on every import, so the webhook will be picked up automatically on next command execution

## Files In Play
- `askr/utils/env.py`
- `askr/cli/askr.py`

## Relational Files
- `.env` (configures): Local .env file now properly read for Discord webhook and other keys
- `~/.config/askr/.env` (configures): Global env file that was previously overriding local .env; now respects local values

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`
