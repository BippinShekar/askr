# Handover: bippin

Last updated: 2026-06-15 13:04

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook initialization bug where local .env keys were being ignored due to early return in env.load()

## Discussion
User reported that Discord webhook wasn't being picked up despite existing in local .env. Root cause identified: env.load() returns early after loading global ~/.config/askr/.env, preventing local .env from being read. Two fixes applied: (1) env.py — changed override=False on local load to allow local keys to supplement global config, (2) askr.py — removed early return in cmd_init so setup_keys() always runs and prompts for webhook. Changes committed and pushed to git.

## Accomplishments
- [x] Identified root cause: env.load() early return preventing local .env from being read
- [x] Fixed env.py to use override=False on local dotenv load, allowing local keys to supplement global config
- [x] Fixed askr.py cmd_init to remove early return and always call setup_keys()
- [x] Committed and pushed both changes to git

## Next Actions
1. User should regenerate Discord webhook URL in Discord server settings (Server Settings → Integrations → Webhooks) since it was exposed in chat
   *Why: Security: exposed webhook URL in chat transcript is a vulnerability*
2. User should pull the latest changes and run `askr init` again to re-prompt for webhook setup
   *Why: The fix ensures setup_keys() now runs and captures the webhook properly*
3. Verify that local .env ASKR_DISCORD_WEBHOOK is now being picked up by running `askr` and checking that Discord integration works
   *Why: Confirm the fix resolves the original issue*

## Decisions
- Use override=False on local dotenv load instead of override=True — Allows local .env keys to supplement (not override) global ~/.config/askr/.env, which is the correct precedence for per-project config
- Remove early return in cmd_init after checking ANTHROPIC_API_KEY — Ensures setup_keys() always runs and prompts for webhook, even if API key already exists

## Failed Approaches
- Assumed the issue was with override=True on local load — Actually override=False was correct; the real bug was the early return in cmd_init preventing setup_keys() from being called

## Files In Play
- `askr/utils/env.py`
- `askr/cli/askr.py`

## Relational Files
- `.env` (configures): Local .env file that should be read by env.load()
- `~/.config/askr/.env` (configures): Global config file that takes precedence but should not block local .env

## Uncommitted Files
- `askr_state/implementation_state.md`
- `roadmap.md`
- `stress-tests/`
