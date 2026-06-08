Last updated: 2026-06-08 19:26

# Project Brief

Askr is a daemon and CLI tool that monitors Claude Code sessions, detects when context or quota limits are about to be exhausted, and automatically checkpoints project state to git before interruption. It enables seamless handoffs between developers and sessions by maintaining persistent state—objectives, decisions, progress—so work can resume without context loss or manual context injection.

## What's In Flight

- Session metrics redesign: building visually polished, shareable metric cards (screenshot/tweet-worthy) that highlight autonomous session continuations as the core value metric rather than generic token counts. New `report_image.py` module created; Discord webhook testing in progress to validate card appearance.
- Autonomous session detection: wired logic into `stop.py` to identify sessions that completed without developer interruption, feeding into report generation.
- Verification: confirming Discord test card was received and meets visual standards; if not, iterate on card template and re-test.

## Key Decisions Made

- State persists in git as append-only decision logs and task snapshots, enabling handoffs without external databases.
- Session lifecycle is split into discrete hooks (start, prompt submit, stop, pre-compact) rather than monolithic monitoring, allowing targeted intervention at safe points.
- Metrics focus on autonomous continuations and context wall avoidance (checkpoint interception) rather than raw token counts—this is the