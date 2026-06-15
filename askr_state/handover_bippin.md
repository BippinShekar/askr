# Handover: bippin

Last updated: 2026-06-15 13:10

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook not being picked up during `askr init` when local .env exists in project directory

## Discussion
Friend's askr clone has a local .env with ASKR_DISCORD_WEBHOOK, but `askr init` fails to send the brief to Discord. Root cause: `env.load()` returns early if ~/.config/askr/.env exists, never loading the local .env. Secondary issue: `setup_keys()` bails early if global .env exists, so it never prompts for webhook. Fixed env.py to use `override=False` on local load (so global keys win but local-only keys still load), and modified cmd_init to explicitly prompt for webhook during init even if global .env exists.

## Accomplishments
- [x] Identified root cause: env.load() early return prevents local .env from being read when global ~/.config/askr/.env exists
- [x] Fixed env.py: changed local load_dotenv to use override=False so both global and local .env keys are merged
- [x] Committed and pushed env.py + askr.py changes to main branch
- [x] Modified cmd_init in askr.py to prompt for Discord webhook during init (line 608) even when global .env exists

## In Progress
- `/Users/bippin/Desktop/askr/askr/cli/askr.py` (line 608): Incomplete git add/commit for the cmd_init webhook prompt fix — command was cut off mid-message

## Next Actions
1. Complete the git commit for askr.py webhook prompt fix: `git add askr/cli/askr.py && git commit -m "fix: prompt for Discord webhook during init even if global .env exists"`
   *Why: The commit message was truncated in the transcript; need to finalize and push this critical fix*
2. Push the completed commit: `git push`
   *Why: Friend needs the fix in main to test the full flow*
3. Have friend run `git pull` in their askr clone, then re-run `askr init` in their project directory
   *Why: This will trigger the new webhook prompt and send the brief to Discord via the local .env webhook*
4. Verify Discord brief arrives in friend's webhook channel after init completes
   *Why: Confirms the fix works end-to-end: local .env webhook is now picked up and used*

## Decisions
- Use override=False on local load_dotenv instead of override=True, so global keys take precedence but local-only keys (like ASKR_DISCORD_WEBHOOK) still get loaded — Allows team to have shared global config while projects can override or add local-only keys without duplication
- Modify cmd_init to explicitly prompt for webhook instead of relying on setup_keys(), which bails early if global .env exists — Ensures every project init captures the correct webhook for that project, even if user has a global .env

## Failed Approaches
- Relying on setup_keys() to prompt for webhook during init — setup_keys() returns early if ~/.config/askr/.env exists, so it never asks for webhook — breaks the init flow for users with global config

## Files In Play
- `askr/cli/askr.py`
- `askr/utils/env.py`

## Relational Files
- `askr/utils/env.py` (imported_by): env.load() is called on every import; the early return bug was blocking local .env from being read
- `askr/cli/askr.py` (configures): cmd_init calls setup_keys() and sends Discord brief; needed to add explicit webhook prompt here

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Git commit for askr.py webhook prompt fix is incomplete (message was truncated) — needs to be finalized and pushed before friend can test
