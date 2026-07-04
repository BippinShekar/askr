# Handover: bippin

Last updated: 2026-07-04 23:29

*Source of truth: `handover_bippin.json`*


## Task
Implemented the per-turn lightweight handover model by adding `askr brief` CLI command for on-demand project brief generation, wiring background handover spawning into stop.py, verifying all 188 tests pass with the new checkpoint architecture, correcting stale decisions about per-turn extraction guarantees and emergency checkpoint triggers, and fixed OAuth cost tracking to report real quota percentage instead of fabricated dollar amounts.

## Discussion
This session completed OAuth cost tracking fixes and verified the entire per-turn handover refactor. Root cause identified: `pre_compact.py` writes the quota-pending flag only when quota is ≥85% at emergency context-kill time; that flag persisted within its 5-minute freshness window, causing a stale voice announcement on the next turn. Fixed by checking live quota % in stop.py before broadcasting. All 188 tests pass. The per-turn handover-only model is fully operational: stop.py spawns async background handover updates via checkpoint.create_handover_only() after every assistant turn without blocking, while heavy checkpoint.create_checkpoint() (git commit, Discord, architecture regen) remains reserved for daemon-triggered emergency conditions only. OAuth cost tracking now reports real quota_five_hour_pct instead of fabricated cost_usd; historical billed entries retain real cost_usd for audit trail.

## Accomplishments
- [x] Fixed stale voice announcement bug: stop.py now checks live quota % before broadcasting, not stale quota-pending flag from pre_compact.py
- [x] Verified all 188 tests pass with checkpoint refactor and OAuth integration
- [x] Corrected decisions.jsonl: voice broadcast fires only on emergency conditions (quota ≥90% or genuine inactivity), never per-turn
- [x] Documented OAuth cost tracking: real quota_five_hour_pct for new calls, real cost_usd for historical billed entries
- [x] Confirmed `ask <query>` CLI uses separate API key, not Claude Code's OAuth token

## Next Actions
1. Monitor production for voice announcement behavior under real quota pressure (≥90%) to confirm the live % check prevents false positives
   *Why: The fix is defensive; real-world validation ensures the stale-flag bug does not resurface*
2. Review and update any monitoring/alerting that depends on cost_usd from OAuth calls; migrate to quota_five_hour_pct as the primary metric
   *Why: OAuth calls no longer report per-call cost; quota % is the only meaningful metric for rate-limit tracking*
3. Document the quota-pending flag lifecycle (5-minute freshness, written only at ≥85% emergency kill) in code comments or architecture guide
   *Why: This subtle timing behavior caused the bug; explicit documentation prevents future confusion*

## Decisions
- Heavy checkpoint.create_checkpoint() (with git commit, Discord broadcast, architecture regen) is reserved exclusively for daemon-triggered emergency conditions (quota/context at 90%, genuine user inactivity), never for per-turn execution — Prevents checkpoint latency from blocking user turns; ensures fast turn completion while maintaining cross-session continuity through lightweight handover updates
- `askr brief` generates project_brief.md on-demand only, not automatically after every session — Reduces checkpoint overhead; brief is a convenience tool for users, not a critical handover artifact
- Voice broadcast fires only on emergency conditions (quota/context at 90% or genuine user inactivity), not per-turn — Prevents notification spam; reserves voice alerts for genuinely critical situations requiring immediate user attention
- Per-turn handover updates are LLM-backed, not deterministic; task/next_actions/files_in_play are extracted via Claude, not computed — Reflects actual implementation: checkpoint.create_handover_only() calls Claude to update state, not a deterministic algorithm
- OAuth-authenticated calls (Claude Code's token) report real quota_five_hour_pct, not fabricated cost_usd — OAuth token does not provide per-call cost data; quota % is the only meaningful metric available; fabricating $ amounts is misleading
- Historical billed entries (pre-OAuth) retain real cost_usd; new OAuth entries use quota_five_hour_pct — Preserves audit trail of actual billing; OAuth calls have no per-call cost, only quota consumption
- `ask <query>` CLI command uses a separate API key, not Claude Code's OAuth token — Isolates user queries from Claude Code's quota; prevents user queries from exhausting the OAuth token's rate limit

## Files In Play
- `askr/hooks/stop.py`
- `tests/test_context_cut_handover.py`

## Relational Files
- `askr/checkpoint.py` (imported_by): stop.py calls checkpoint.create_handover_only() to spawn background handover updates
- `askr_state/decisions.jsonl` (configures): Architectural decisions about checkpoint scope, voice broadcast, and cost tracking
- `askr_state/handover_bippin.json` (configures): Project state handover document updated with session accomplishments
