# Handover: bippin

Last updated: 2026-06-15 13:48

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook prompt and initialization flow so friend can successfully run `askr init` and post project brief to Discord

## Discussion
The friend ran `askr init` but Discord send failed because the webhook wasn't configured. Root cause: `setup_keys()` bails early if `~/.config/askr/.env` exists, never prompting for the webhook. The repo's `.env` isn't loaded during `askr init` because it runs from the project folder, not the clone. Fixed by adding a prompt in `cmd_init` to detect missing `ASKR_DISCORD_WEBHOOK` and ask the user to paste it. Then discovered `getpass` hides input (meant for passwords), so the prompt text shows but typed URL is invisible — user thinks nothing happened. Second fix: skip Discord send entirely if no webhook is configured, and use `input()` instead of `getpass()` so the URL is visible during entry.

## Accomplishments
- [x] Added webhook prompt to cmd_init that detects missing ASKR_DISCORD_WEBHOOK and asks user to paste URL
- [x] Fixed Discord send to bail out early if no webhook is configured instead of printing 'send failed'
- [x] Identified that getpass() hides input — need to switch to input() for visible URL entry

## In Progress
- `/Users/bippin/Desktop/askr/askr/cli/askr.py` (line 613): Webhook prompt and Discord send logic in cmd_init — last edit at line 613 (13:47). Commit message incomplete: 'fix: skip Discord send entirely if no' — needs completion and push

## Next Actions
1. Complete and push the uncommitted git commit for askr.py (message was cut off: 'fix: skip Discord send entirely if no webhook configured')
   *Why: Changes are staged but commit message incomplete and not pushed; friend can't pull the fix yet*
2. Replace getpass() with input() in the webhook prompt so the pasted URL is visible to the user
   *Why: User sees no feedback when pasting URL with getpass, thinks the prompt didn't work — input() shows typed text*
3. Have friend pull latest, then run `askr init` in project directory — should now prompt for webhook, accept it, save to ~/.config/askr/.env, and successfully post brief to Discord
   *Why: This is the end-to-end test of the fix; if webhook prompt appears and Discord send succeeds, the issue is resolved*
4. If Discord still fails after friend enters webhook, check that load_dotenv() is loading ~/.config/askr/.env before send_message() runs
   *Why: Webhook might be saved but not loaded into environment if dotenv call happens at wrong time*

## Decisions
- Skip Discord send entirely if ASKR_DISCORD_WEBHOOK is not in environment, rather than printing 'send failed' — Cleaner UX — no confusing error message if user skips the prompt; silent skip is acceptable for optional feature
- Prompt for webhook in cmd_init (during `askr init`) rather than during daemon startup or first command — Webhook is project-specific and should be configured once at init time; asking during every command would be annoying

## Failed Approaches
- Using getpass() to prompt for webhook URL — getpass() hides input (designed for passwords), so user sees prompt but no visible feedback when typing/pasting URL — appears broken
- Relying on repo's .env to be loaded during `askr init` without explicit prompt — setup_keys() returns early if ~/.config/askr/.env exists, never reading repo .env; user has no way to configure webhook if global file exists

## Files In Play
- `/Users/bippin/Desktop/askr/askr/cli/askr.py`

## Relational Files
- `/Users/bippin/Desktop/askr/askr/env.py` (imported_by): Contains load_dotenv() and setup_keys() logic that cmd_init calls; webhook prompt fix depends on understanding when env is loaded
- `/Users/bippin/Desktop/askr/askr/discord.py` (imported_by): Contains send_message() that cmd_init calls; needs to handle missing webhook gracefully

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Git commit message for askr.py fix is incomplete ('fix: skip Discord send entirely if no') — needs to be completed and pushed before friend can pull
