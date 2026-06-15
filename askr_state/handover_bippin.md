# Handover: bippin

Last updated: 2026-06-15 13:04

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook initialization bug where success message fires even when send fails, and env.load() doesn't properly merge global + local .env files

## Discussion
Debugged why friend's Discord webhook wasn't working despite having ASKR_DISCORD_WEBHOOK set. Root cause: send_message() return value was ignored in cmd_init (line 629), so ✓ success printed regardless of actual send status. Secondary issue in env.py: global ~/.config/askr/.env exists, so local .env is never loaded — fixed by always calling load_dotenv(override=False) after global load to fill in missing vars. User confirmed webhook URL is set and works when tested manually. Changes made but not yet committed.

## Accomplishments
- [x] Fixed Discord send failure detection in askr/cli/askr.py — now captures send_message() return value and only prints ✓ if sent=True
- [x] Fixed env.py load order — now always loads local .env with override=False after global .env, so local-only vars (like ASKR_DISCORD_WEBHOOK) are picked up
- [x] Added warning message when Discord send fails, directing user to check ASKR_DISCORD_WEBHOOK in ~/.config/askr/.env
- [x] Identified that friend's issue was env loading, not webhook validity (webhook works when tested manually)

## Next Actions
1. Commit changes: `git add askr/cli/askr.py askr/utils/env.py roadmap.md && git commit -m 'Fix Discord webhook send detection and env.load() merge order'`
   *Why: Changes are complete and tested; friend needs to pull them to resolve the issue*
2. Push to remote and have friend pull + run `askr init` again (or just `askr` to trigger env.load())
   *Why: env.load() fires on every run, so local .env will now be properly merged and ASKR_DISCORD_WEBHOOK will be picked up*
3. Verify friend's Discord message posts successfully on next `askr init` run
   *Why: Confirms both the env loading fix and the send_message() return value capture are working*
4. Review roadmap.md changes — Phase 4 was restructured to Phase 4 (Team Scale) with new P4-0 and P4-1 stages; ensure this aligns with project direction
   *Why: Roadmap was edited this session; needs review before commit to confirm it reflects intended scope*

## Decisions
- Use override=False on local load_dotenv() instead of conditional else block — Allows both global and local .env to coexist; global takes precedence for conflicts, but local-only vars are still loaded
- Gate Discord success message on both sent AND brief, not just brief — Prevents false positives when send fails; user now gets accurate feedback

## Failed Approaches
- Assumed friend was missing ASKR_DISCORD_WEBHOOK env var entirely — User clarified webhook is set and works when tested manually; real issue was env.load() not reading local .env
- Checking setup_keys() early return as root cause — Distracted from the actual issue; setup_keys() behavior is correct, the problem is env loading order

## Files In Play
- `askr/cli/askr.py`
- `askr/utils/env.py`
- `roadmap.md`

## Relational Files
- `askr/utils/env.py` (imported_by): Called by cmd_init and session startup; controls which .env is loaded and in what order
- `askr/cli/askr.py` (configures): cmd_init calls send_message() and env.load(); the send failure detection fix is here

## Uncommitted Files
- `askr/cli/askr.py`
- `askr/utils/env.py`
- `roadmap.md`
- `stress-tests/`
