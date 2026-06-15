# Handover: bippin

Last updated: 2026-06-15 14:31

*Source of truth: `handover_bippin.json`*


## Task
Fix macOS SSL certificate verification error in Discord webhook client and establish per-repo webhook configuration strategy

## Discussion
Friend encountered SSL certificate verification failure on macOS when Discord webhook tried to send. Root cause: Python on macOS doesn't use system certificates by default. Applied `certifi` library fix to both `send_message` and `send_file` methods in discord.py. User then raised critical architectural question: how should askr differentiate between repos and support different webhooks per repo, since current design stores keys globally in `~/.config/askr/.env`. This exposed a gap between the single-key-per-machine model and the user's need for private vs. official project separation.

## Accomplishments
- [x] Added certifi SSL context to discord.py send_message method
- [x] Added certifi SSL context to discord.py send_file method
- [x] Added certifi to requirements.txt
- [x] Committed SSL fix and verified install.sh will auto-install certifi

## Next Actions
1. Design per-repo webhook configuration system: decide between (a) repo-level .env override in askr_state/, (b) team/project scoping in Phase 4 structure, or (c) environment variable per-repo pattern
   *Why: User explicitly needs different webhooks for private vs official projects; current global-only design blocks this use case*
2. Update askr init to optionally prompt for repo-specific webhook URL if not found in global config
   *Why: Enables per-repo differentiation without breaking existing single-key workflows*
3. Document in CLAUDE.md or README how to set repo-specific Discord webhooks for team/project separation
   *Why: User needs clear guidance on the intended workflow for managing multiple projects*
4. Verify friend's SSL fix works: git pull, re-run install.sh, askr init, test Discord send
   *Why: Unblock immediate blocker before architectural changes*

## Decisions
- Global keys in ~/.config/askr/.env are shared across all repos on a machine — Simplest initial design; setup happens once, not per-project
- setup_keys() only runs when ~/.config/askr/.env doesn't exist — Avoid re-prompting on every askr init; keys are machine-level, not project-level

## User-Rejected Approaches
- **Global keys are sufficient for all use cases; askr init just sets up state files and hooks** — "then how will askr differentiate between repo's? also, what if I want to have different webhooks for differnt repo's?" (domain: webhook configuration, project isolation)

## Failed Approaches
- Assuming single global webhook URL works for all repos — User has legitimate need to separate private and official projects with different Discord webhooks

## Files In Play
- `askr/clients/discord.py`
- `requirements.txt`

## Relational Files
- `askr/hooks/notification.py` (calls): Calls discord.py send methods; error messages now propagate SSL details
- `askr/cli/askr.py` (imported_by): Contains setup_keys() and askr init logic; needs update for per-repo webhook support
- `install.sh` (configures): Runs pip install -r requirements.txt; will auto-install certifi after this session's commit
- `roadmap.md` (documents): Phase 4 team scoping may address per-repo/per-team webhook differentiation

## Uncommitted Files
- `roadmap.md`
- `stress-tests/`

## Blockers
- Architectural decision needed: how to support per-repo webhook URLs without breaking global key model
