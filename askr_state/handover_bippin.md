# Handover: bippin

Last updated: 2026-06-15 14:34

*Source of truth: `handover_bippin.json`*


## Task
Implement per-project Discord webhook configuration to allow different repos to use different Discord servers for notifications

## Discussion
User needed per-repo webhook support to keep private and shared projects isolated across different Discord servers. Current implementation uses only global env vars. Built a three-stage solution: (1) add `askr_state/config.json` for per-project settings, (2) update `discord.py` to check project config before falling back to global env, (3) update `askr init` to prompt for and save project-specific webhook. This enables team workflows where private projects and shared projects can post to separate Discord channels without requiring separate global key management.

## Accomplishments
- [x] Created `askr/state/config.py` with per-project config functions to read/write `askr_state/config.json`
- [x] Updated `askr/clients/discord.py` to resolve webhook from project config first, then fall back to global `ASKR_DISCORD_WEBHOOK` env var
- [x] Updated `cmd_init` in `askr/cli/askr.py` to prompt user for project-specific Discord webhook and save it to project config
- [x] Staged all three files for commit with git add (commit message incomplete in transcript)

## In Progress
- `/Users/bippin/Desktop/askr/askr/state/config.py` (line 58): Per-project config module with load/save functions for `askr_state/config.json`
- `/Users/bippin/Desktop/askr/askr/clients/discord.py` (line 65): Webhook resolution logic updated to check project config before global env var
- `/Users/bippin/Desktop/askr/askr/cli/askr.py` (line 608): `cmd_init` updated to prompt for and save project webhook to config

## Next Actions
1. Complete the git commit that was started — run `git commit -m "feat: per-project discord webhook configuration"` to finalize the three-stage implementation
   *Why: Changes are staged but commit message was cut off in transcript; need to complete the commit to lock in the feature*
2. Test `askr init` in a fresh repo to verify it prompts for webhook and saves to `askr_state/config.json`
   *Why: Confirm the user-facing flow works end-to-end before shipping*
3. Test webhook resolution by setting a project-specific webhook in one repo and global webhook in env, then verify Discord messages use the project one
   *Why: Validate the fallback logic works correctly and project config takes precedence*
4. Update `CLAUDE.md` or docs to explain the per-project webhook feature and how to set it up
   *Why: Users need to understand they can now configure different webhooks per repo during `askr init`*
5. Consider adding `askr config` CLI command to view/edit project config without re-running `askr init`
   *Why: Users may want to change webhook later without reinitializing the entire project state*

## Decisions
- Store per-project webhook in `askr_state/config.json` rather than `.env` file in project root — Keeps all project state in one directory (`askr_state/`), avoids polluting repo root, and maintains consistency with existing state structure
- Check project config first, then fall back to global env var, rather than requiring one or the other — Allows gradual adoption — existing users with only global env var continue to work, new users can set per-project overrides
- Prompt for webhook during `askr init` rather than in a separate `askr config` command — Captures the webhook at setup time when user is already configuring the project, reducing friction

## Files In Play
- `askr/state/config.py`
- `askr/clients/discord.py`
- `askr/cli/askr.py`
- `requirements.txt`

## Relational Files
- `askr/state/__init__.py` (imports): May need to export config functions for use elsewhere in the codebase
- `askr_state/config.json` (configures): New file that stores per-project webhook and other settings; created by `askr init`
- `askr/cli/commands/init.py` (imported_by): If `cmd_init` is in a separate file, it will import the new config functions

## Uncommitted Files
- `askr_state/implementation_state.md`
- `roadmap.md`
- `stress-tests/`
