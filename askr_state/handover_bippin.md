# Handover: bippin

Last updated: 2026-06-15 14:30

*Source of truth: `handover_bippin.json`*


## Task
Fix macOS SSL certificate verification error in Discord webhook client and ensure multi-project setup with separate tracking

## Discussion
Friend encountered SSL certificate verification failure on macOS when Discord webhook tried to send notifications. Root cause: Python on macOS doesn't use system certificates by default. Solution implemented: added `certifi` library to provide proper SSL context for both `send_message` and `send_file` methods in discord.py. User confirmed that `askr init` in a new repo will prompt for Anthropic key and webhook URL again, enabling separate tracking for private vs official projects as required.

## Accomplishments
- [x] Fixed SSL certificate verification in discord.py by adding certifi SSL context to urllib requests
- [x] Added certifi to requirements.txt
- [x] Committed changes to discord.py and requirements.txt with git
- [x] Verified that askr init prompts for credentials per-repo, enabling multi-project separation

## Next Actions
1. Friend runs `git pull` to fetch the certifi fix and updated requirements.txt
   *Why: Pulls the SSL certificate fix into their local repo*
2. Friend runs `install.sh` to reinstall dependencies and pick up certifi into the venv
   *Why: install.sh runs pip install -r requirements.txt which will install certifi automatically*
3. Friend runs `askr init` in the new repo to set up Anthropic key and Discord webhook URL separately
   *Why: Enables separate tracking for private projects vs official projects with distinct credentials*
4. Test Discord notification by triggering a session to verify SSL error is resolved
   *Why: Confirms the certifi fix resolves the [SSL: CERTIFICATE_VERIFY_FAILED] error*

## Decisions
- Use certifi library for SSL context instead of disabling certificate verification — Secure approach that respects certificate validation while providing macOS Python with proper certificate bundle
- Apply certifi fix to both send_message and send_file methods in discord.py — Both methods use urllib and both can encounter SSL verification failures

## Files In Play
- `askr/clients/discord.py`
- `requirements.txt`

## Relational Files
- `askr/cli/askr.py` (imported_by): Calls discord client for notifications
- `askr/hooks/notification.py` (imported_by): Uses discord client to send notifications
- `install.sh` (configures): Runs pip install -r requirements.txt to install certifi

## Uncommitted Files
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`
