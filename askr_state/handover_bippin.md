# Handover: bippin

Last updated: 2026-06-15 14:02

*Source of truth: `handover_bippin.json`*


## Task
Debug why `askr init` is not auto-loading Discord webhook URL from .env file when friend runs it in the cloned askr folder with a manually created .env

## Discussion
Friend cloned the repo, copied example.env, added his own Discord webhook key, ran `askr init` in the askr folder, but the webhook prompt still appeared instead of auto-loading the value. Root cause: `load_dotenv()` in env.py was not being called with the correct path to find the .env in the askr repo root. Two fixes were attempted: (1) moving the webhook prompt outside the try-except to ensure it runs, (2) updating env.py to compute the repo root from __file__ and always load .env from there. User clarified the friend DID create a .env file manually with keys and ran init in the correct folder, so the issue is purely about load_dotenv() not finding or loading that file.

## Accomplishments
- [x] Identified that except Exception: pass was swallowing import errors before webhook prompt
- [x] Moved Discord webhook prompt outside try-except block in askr.py
- [x] Updated env.py to compute repo root from __file__ path and always load .env from there
- [x] Committed both fixes to git

## In Progress
- `askr/utils/env.py`: Verify load_dotenv() is correctly resolving to the .env in the askr repo root and actually loading ASKR_DISCORD_WEBHOOK

## Next Actions
1. Have friend run `git pull` to get the latest fixes, then delete any cached .env state and run `askr init` again from inside the askr folder
   *Why: The fixes are committed; need to verify they actually work end-to-end with a fresh clone*
2. If webhook prompt still appears, add debug logging to env.py to print the computed repo root path and whether load_dotenv() found the .env file
   *Why: Need visibility into whether load_dotenv() is even finding the file or if there's a path resolution issue*
3. Check if the .env file in the askr folder is actually being read by Python (file permissions, encoding, format of the ASKR_DISCORD_WEBHOOK line)
   *Why: File might exist but be unreadable or malformed*
4. Verify that os.getenv('ASKR_DISCORD_WEBHOOK') is being called AFTER load_dotenv() in the init flow
   *Why: If getenv is called before load_dotenv completes, the env var won't be populated*

## Decisions
- Move webhook prompt outside try-except instead of keeping it inside — Ensures the prompt always runs and cannot be swallowed by exception handling
- Compute repo root from env.py's __file__ path rather than relying on working directory — Makes load_dotenv() work regardless of where `askr init` is invoked from

## User-Rejected Approaches
- **The .env file is gitignored and doesn't exist in the clone** — "bro, don't act like some 4th grader, my friend cloned the repo, copied the example .env file, and added his own keys" (domain: askr/utils/env.py, askr/cli/askr.py)

## Failed Approaches
- Assumed .env was not in the repo at all and needed to be created — User clarified friend already created .env manually from example.env with his own keys

## Files In Play
- `askr/cli/askr.py`
- `askr/utils/env.py`

## Relational Files
- `example.env` (configures): Friend copied this to create his .env with Discord webhook key
- `.gitignore` (configures): Determines whether .env is tracked in git (it is not)

## Uncommitted Files
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Cannot verify the fixes work until friend runs `git pull` and tests `askr init` again with the updated code
