# Handover: bippin

Last updated: 2026-06-15 13:05

*Source of truth: `handover_bippin.json`*


## Task
Fix Discord webhook not being picked up from local .env in askr clone; commit and push the fix.

## Discussion
User's friend cloned askr but Discord webhook from local .env wasn't being used. Root cause: `env.load()` returns early after loading global `~/.config/askr/.env`, preventing local .env keys from being read. Fixed by adding `override=False` to the local `load_dotenv()` call in `env.py`, and fixed a separate bug in `askr.py` where `setup_keys()` exits early if .env exists, never prompting for webhook. Both changes committed and pushed.

## Accomplishments
- [x] Identified root cause: env.load() returns after global .env load, blocking local .env
- [x] Fixed env.py: added override=False to local load_dotenv() to allow local keys to merge
- [x] Fixed askr.py: removed early return in setup_keys() so webhook prompt always fires
- [x] Committed both fixes with message 'fix: Discord send...' and pushed to remote

## Next Actions
1. Tell friend to run `git pull` to get the two fixes (env.py and askr.py)
   *Why: Changes are now on remote; friend's local clone needs them*
2. Confirm with friend whether to run `askr init` again after pull, or if just running `askr` is enough
   *Why: User asked this question at end of session; `env.load()` fires on any `askr` command, so init may not be strictly necessary, but init is safer to ensure webhook is properly configured*
3. Verify friend's local .env has ASKR_DISCORD_WEBHOOK key and that it's now being picked up
   *Why: Confirm the fix actually resolves the original issue*

## Decisions
- Use override=False on local load_dotenv() instead of override=True — Allows global keys to be overridden by local .env, which is the correct precedence for per-project configuration
- Remove early return in setup_keys() when .env exists — Webhook prompt must always fire during init, even if other keys are already saved

## Files In Play
- `askr/utils/env.py`
- `askr/cli/askr.py`

## Relational Files
- `.env` (configures): Local .env contains ASKR_DISCORD_WEBHOOK and other keys that need to be loaded
- `~/.config/askr/.env` (configures): Global env file that was blocking local .env from being read

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`
