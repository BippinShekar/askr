# Handover: bippin

Last updated: 2026-07-06 19:39

*Source of truth: `handover_bippin.json`*


## Task
Diagnosed and fixed three critical bugs in activity tracking, handover generation, and session continuity that were causing false inactivity alerts, incorrect quota announcements, and unwanted session auto-launches; identified that session continuity via stop hook does not preserve stage-plan context when autonomous handover jobs run between user interactions.

## Discussion
The askr system had three interconnected bugs: (1) idle trigger (Trigger C) was being announced as a quota emergency and auto-launching new sessions, (2) the idle threshold was measuring time since last completed turn rather than actual user inactivity, and (3) session continuity via the stop hook was not preserving stage-plan context when autonomous jobs ran between user interactions. This session confirmed the user's clarification that the continuity problem extends beyond mid-session companion opens to include autonomous handover jobs that run after context-switch stops—when a multi-step stage plan is interrupted mid-implementation, the autonomous job (e.g., git save, test runner) has no knowledge of remaining stages. Root causes traced to lifecycle.py's code-path reuse across different trigger types (quota, context, idle) causing semantic mismatches, and to checkpoint.py's _build_transcript_text() stripping tool inputs that would preserve plan context.

## Accomplishments
- [x] Confirmed three separate bugs in idle trigger, idle threshold measurement, and session continuity via stop hook
- [x] Identified root cause: _build_transcript_text() in checkpoint.py strips all tool input except Write/Edit/MultiEdit/Bash, losing plan context
- [x] Traced idle trigger false announcements to code-path reuse between quota/context/idle trigger types in lifecycle.py
- [x] Documented that autonomous handover jobs (via stop hook) lack visibility into multi-stage plans interrupted mid-implementation

## In Progress
- `askr/session/checkpoint.py` (line 137): Preserve full tool input context in _build_transcript_text() to maintain stage-plan visibility across autonomous handover jobs; enforce token limits via API call parameters, not post-generation truncation
- `askr/session/lifecycle.py` (line 140): Decouple idle trigger semantics from quota/context trigger code paths; ensure idle conditions do not trigger session auto-launch or quota announcements

## Next Actions
1. Modify _build_transcript_text() in checkpoint.py to preserve full tool input for all block types, not just Write/Edit/MultiEdit/Bash; this restores stage-plan context in autonomous handover jobs
   *Why: Current stripping loses the user's multi-step plan when autonomous job runs between context-switch stops; full context is needed for next Claude session to understand remaining stages*
2. Enforce token limits via max_tokens parameter in call_claude() rather than post-generation truncation; if token enforcement is not possible, require Claude to wrap required outputs in <required></required> tags
   *Why: User rejected mindless truncation of LLM outputs; truncating after generation wastes compute and loses semantic structure; enforcement at call time is cleaner*
3. Audit all call_claude() invocations to ensure max_tokens is set appropriately and no post-response truncation occurs
   *Why: Establishes baseline for token-limit enforcement; prevents future truncation bugs*
4. Test autonomous handover job flow with multi-stage plan: implement stage 1-4, trigger context-switch stop, verify autonomous job preserves remaining stages in handover for next session
   *Why: Validates that session continuity bug is fixed; confirms stage-plan context survives autonomous job boundary*

## Decisions
- Historical billed entries (pre-OAuth) retain cost_usd for audit trail; new OAuth entries use quota_five_hour_pct only — Maintains backward compatibility with existing cost records while accurately reflecting OAuth's data limitations
- Idle trigger uses dedicated _checkpoint_idle_inactivity() function, not generic _execute_trigger() shared with quota/context triggers — Idle semantics (user absence from app) differ fundamentally from quota/context semantics (resource exhaustion); code-path reuse caused false announcements and unwanted session launches
- Voice broadcast fires only on emergency conditions (quota/context at 90%+), never per-turn — Per-turn announcements create spam and false urgency; emergencies are rare and warrant interruption
- ask CLI uses separate API key, not Claude Code's OAuth token — Keeps CLI and Claude Code authentication domains separate; prevents quota/cost confusion between interactive and CLI usage

## User-Rejected Approaches
- **Truncate LLM outputs based on character or token limits after generation** — "no sort of manual truncation must be done, any truncation to LLM outputs will not be allowed, if we need truncated responses, let's enforce it via the calls" (domain: askr/session/checkpoint.py, call_claude() invocations)

## Files In Play
- `askr/session/lifecycle.py`
- `askr/session/checkpoint.py`

## Relational Files
- `askr/session/lifecycle.py` (imports): Defines idle trigger logic and _execute_trigger() code path that was causing false announcements
- `askr/session/checkpoint.py` (imported_by): Contains _build_transcript_text() that strips tool inputs, losing stage-plan context in autonomous handover jobs
- `askr_state/decisions.jsonl` (configures): Records architectural decisions about trigger semantics and API authentication

## Blockers
- Session continuity bug requires changes to both checkpoint.py (preserve tool input) and lifecycle.py (decouple idle trigger); both must be coordinated to avoid regressions
