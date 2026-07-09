# Handover: bippin

Last updated: 2026-07-09 14:33

*Source of truth: `handover_bippin.json`*


## Task
The askr system implemented a Phase 5 approval gate for autonomous session relaunch (quota-trigger, context-trigger, goal-autolaunch) that holds dangerous sessions pending explicit approval, added IDE popup handlers for task_approval_pending and guard_warning notifications, fixed critical transcript-truncation bugs, race conditions in lifecycle triggers, false-positive idle-trigger fires, phantom-session warnings, cross-process voice serialization, and unified terminal/IDE statusline labeling for context-window percentage display.

## Discussion
This session completed a small labeling fix: the terminal statusLine and CLI output were displaying context-window percentage as 'ctx:X%' while the IDE extension already showed 'chat X%'. Both surfaces measure the same metric; the session unified the label to 'chat' across both terminal and CLI output to match the extension. During investigation, the session also diagnosed root causes for repeated quota/context warnings: the quota dedup memory (quota_triggered_windows.json) remains empty when quota_reset_at is not yet populated from a usage-API refresh, allowing the hard trigger to re-fire on every poll cycle; the context trigger spawns new companion sessions with fresh dedup slates, cascading when injected context is already high at startup (Phase 3.15 smart context injection not yet shipped). A third issue was identified: talk-only research sessions fall back to weak git-log clustering (0.50 confidence) when no strong signals fire, leaving next_actions unpopulated for the next session.

## Accomplishments
- [x] Fixed terminal statusline label to match IDE extension: unified 'chat X%' label for per-chat context-window percentage across all UI surfaces
- [x] Diagnosed root cause of repeated quota-trigger announcements: dedup memory (quota_triggered_windows.json) remains empty when quota_reset_at is not yet populated from usage-API refresh
- [x] Diagnosed root cause of repeated context-trigger announcements: companion session relaunch creates new session_id, resetting dedup slate; cascades when injected context is already high at startup
- [x] Identified weak signal fallback in talk-only research sessions: next_actions not reliably populated when no strong signals fire, leaving next session without concrete instruction

## Next Actions
1. Implement fix A: don't fire the quota hard-trigger when quota_reset_at is empty — wait for a real usage-API reading instead of firing blind with no dedup memory
   *Why: Small, isolated, safe fix that mirrors how the soft 75% warning already gates on reset_at; eliminates repeated 'quota at X%' announcements during the initial session window before first usage-API refresh*
2. Prioritize Phase 3.15 (smart context injection) — implement selective context inclusion instead of full-dump at session start to prevent companion sessions from starting with already-high context
   *Why: Root cause of context-trigger cascade; already on pre-launch roadmap; fixes the architectural gap that allows new companion sessions to immediately re-trigger the context warning*
3. Investigate why Signal 3 (handover_next_actions) isn't reliably catching talk-only research sessions; audit recent handover JSON next_actions quality and strengthen weak-signal fallback
   *Why: Talk-only sessions currently fall back to 0.50 confidence (git-log clustering), leaving next session without actionable instruction; this is Phase 3.13 S2-S5 gap (rejected/decided context doesn't persist strongly across session boundaries)*

## Decisions
- All voice output across independent processes (daemon trigger thread, per-turn background handover async pings, hook processes) is serialized via cross-process flock to prevent concurrent `say` invocations from overlapping — Multiple independent OS processes call speak()/speak_signature() with no coordination; concurrent invocations play on top of each other and audibly garble into nonsense. A shared lock file ensures only one process speaks at a time, and speak_signature's prefix+body pair is locked as one atomic unit to prevent interleaving.
- Autonomous session relaunch (quota-trigger, context-trigger, goal-autolaunch) is gated on dangerous session permissions: when triggering session has --dangerously-skip-permissions or equivalent unrestricted Bash/rm access, relaunch is held pending explicit `askr launch approve` — Companion sessions inherit the exact same zero-friction permission state from their triggering session; without a gate, a dangerous session's autonomous relaunch would bypass approval entirely. Checkpointing still happens either way; only the new-terminal spawn is held, mirroring the task-approval model.
- IDE notifications task_approval_pending and guard_warning are rendered as purpose-built popups with context-specific actions (Approve/Discard buttons for task_approval_pending, informational-only for guard_warning) rather than generic fallback messages — Generic fallback handling left users with no way to act on these notifications; purpose-built cases provide clear action paths and match the non-blocking design intent in roadmap Phase 3.5
- Terminal statusline and CLI output use unified label 'chat X%' for per-chat context-window percentage, matching IDE extension display — Both surfaces measure the same metric; using identical labels eliminates user confusion and provides consistent terminology across all UI surfaces

## Files In Play
- `askr/cli/askr.py`

## Relational Files
- `askr/lifecycle.py` (imported_by): Contains quota-trigger and context-trigger logic; quota_reset_at population and dedup key handling at lines 1400-1414, 1612; context-trigger dedup at lines 761-769
- `askr/session/post_tool_use.py` (imported_by): Handles usage-API refresh that populates quota_reset_at; lines 73-88 show the condition where fresh stats files lack reset_at
- `askr/session/stop.py` (imported_by): Contains Stop-hook outcomes direction_proposal and direction_confirm; lines 302-318 show confidence gating and weak signal fallback
- `~/.config/askr/quota_triggered_windows.json` (configures): Dedup memory for quota hard-trigger; remains empty when quota_reset_at is not yet populated, allowing re-fires on every poll cycle
- `~/.config/askr/companioned_sessions.json` (configures): Tracks 57 distinct session IDs; context-trigger dedup is keyed by session_id, resetting on companion session relaunch
