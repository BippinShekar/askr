# Handover: bippin

Last updated: 2026-06-05 14:38

## Task
Add Discord notification system to Phase 3 of askr roadmap to enable team collaboration updates, replacing Slack/Jira dependency for small teams.

## Status
- roadmap.md — Phase 3 updated with `project_brief.md` addition for co-founder/intern handoff clarity. Committed and pushed to git.
- askr core architecture — Session continuity and goal tracking functional. Morning report metrics exist but lack team distribution mechanism.
- Discord integration — Not yet implemented. Concept validated in discussion but no code written.

## Failed Approaches
None.

## Next Action
Create askr/notifications/discord_integration.py with a Discord webhook handler that:
1. Triggers post-session when user session limit reached or at end-of-day
2. Sends formatted message to Discord channel containing: goals completed, session summary, user who ran session
3. Make it configurable via environment variable for Discord webhook URL
Start with skeleton implementation that accepts session data dict and formats/sends to Discord.

## Open Questions
- Which Discord channel should notifications post to by default (configurable per team)?
- Should notifications include code diffs or only high-level goal/task summaries?
- Does this feature belong in Phase 3 or should it be Phase 4 (timing/scope)?
- How to handle authentication/permissions for multiple team members
