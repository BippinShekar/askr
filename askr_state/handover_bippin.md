# Handover: bippin

Last updated: 2026-06-15 13:13

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook initialization flow so `askr init` prompts for webhook URL when global config doesn't exist, instead of silently failing.

## Discussion
The friend ran `askr init` but got a Discord send failure because the webhook wasn't in `~/.config/askr/.env`. Root cause: `setup_keys()` bails early if the global config file exists (even empty), and `askr init` doesn't read the repo's `.env` file. The fix was to make `cmd_init` detect a missing webhook and prompt the user to paste it, saving to the global config. User then questioned whether `askr init` should read from the repo's `.env` first — clarified that the env.py fix now loads global config first, then repo config, so the webhook can come from either source.

## Accomplishments
- [x] Modified askr.py cmd_init to detect missing Discord webhook and prompt user to add it during init
- [x] Committed changes to env.py and askr.py with fixes for webhook detection and loading order
- [x] Pushed changes so friend can pull and re-run askr init with proper webhook prompt

## Next Actions
1. Friend pulls latest changes and runs `askr init` in project directory — should now be prompted for Discord webhook URL if not in global ~/.config/askr/.env
   *Why: Validates the fix works end-to-end; webhook should be saved and next command should post brief to Discord*
2. Verify Discord brief posts successfully after webhook is saved during init
   *Why: Confirms the initialization flow is complete and webhook is being picked up correctly*
3. Test that subsequent `askr` commands use the webhook without re-prompting
   *Why: Ensures env.load() on import correctly reads the saved webhook from global config*
4. Document the init flow in README: repo `.env` is read as fallback, but global `~/.config/askr/.env` takes precedence
   *Why: Clarifies for users where webhook can be stored and which takes priority*

## Decisions
- Global `~/.config/askr/.env` is loaded first, then repo `.env` as fallback — not the other way around — Allows user to override repo settings with personal config; prevents accidental commits of personal webhooks to git
- `askr init` must prompt for webhook if not found in either location, rather than silently failing — Improves UX — user gets immediate feedback and can fix the issue in one step instead of debugging config files

## User-Rejected Approaches
- **Only read webhook from repo `.env` during `askr init`, not from global config** — "but he won't get the project brief for the repo to his discord right? ... shouldn't it take from the .env setup that exists in the repo already?" (domain: env.py, askr.py cmd_init)

## Failed Approaches
- Relying on `setup_keys()` to handle webhook prompting during init — it bails early if global config exists — User never gets prompted if ~/.config/askr/.env already exists, even if webhook is missing or empty
- Only reading repo `.env` during init without checking global config first — Doesn't allow personal webhook overrides and forces webhook to be committed to git

## Files In Play
- `askr/cli/askr.py`
- `askr/utils/env.py`

## Relational Files
- `~/.config/askr/.env` (configures): Global config file where webhook is saved after user prompts during init
- `.env` (configures): Repo-level config that serves as fallback if global config doesn't have webhook
- `roadmap.md` (imported_by): Uncommitted changes show Phase 4 restructuring — not directly related to this session but in working directory

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`
