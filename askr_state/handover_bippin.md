# Handover: bippin

Last updated: 2026-06-15 13:12

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook configuration so local .env files are picked up during askr init, and ensure the brief is sent to Discord on first run.

## Discussion
The core issue was that `env.load()` returned early when `~/.config/askr/.env` existed, preventing local project `.env` files (containing `ASKR_DISCORD_WEBHOOK`) from being loaded. Additionally, `setup_keys()` bailed early if the global config existed, so it never prompted for the webhook. Two fixes were committed: (1) changed `load_dotenv()` to use `override=False` on local load so global keys win but local-only keys are still picked up, and (2) modified `cmd_init` to detect missing webhook and prompt the user to paste it, saving to `~/.config/askr/.env`. User's friend now sees the Discord send failure warning, indicating the webhook is missing and needs to be provided during init.

## Accomplishments
- [x] Fixed env.py to load local .env with override=False, allowing local-only keys like ASKR_DISCORD_WEBHOOK to be picked up while global config takes precedence for shared keys
- [x] Modified cmd_init in askr.py to detect missing ASKR_DISCORD_WEBHOOK and prompt user to paste the URL, saving it to ~/.config/askr/.env
- [x] Committed and pushed both changes to git

## Next Actions
1. User's friend should run `git pull` to get the latest changes from the askr repo
   *Why: The fixes for env loading and webhook prompt have been pushed and need to be in the friend's local copy*
2. Friend should run `askr init` again in the project directory after pulling
   *Why: The updated cmd_init will now detect the missing webhook and prompt for it, saving it to the global config so the brief can be sent to Discord*
3. When prompted during askr init, friend should paste the Discord webhook URL from their server settings
   *Why: This is the missing credential that was causing the 'Discord send failed' warning*
4. Verify that the project brief is successfully posted to Discord after init completes
   *Why: This confirms the webhook is working and the integration is complete*

## Decisions
- Use `override=False` on local .env load instead of skipping it entirely when global config exists — Allows local-only keys (like project-specific webhooks) to be picked up while still respecting global config precedence for shared keys
- Prompt for webhook during askr init rather than requiring manual file editing — Improves user experience and ensures the webhook is saved to the correct location (~/.config/askr/.env) automatically

## Failed Approaches
- Expecting the webhook to be read from the project's local .env file during init — The early return in env.load() when global config exists prevented local .env from being loaded; also setup_keys() bailed early if global config existed, so it never prompted for the webhook

## Files In Play
- `askr/utils/env.py`
- `askr/cli/askr.py`

## Relational Files
- `~/.config/askr/.env` (configures): Global configuration file where webhook and other credentials are stored; loaded by env.py on every import
- `.env` (configures): Local project .env file that may contain project-specific credentials like ASKR_DISCORD_WEBHOOK

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`
