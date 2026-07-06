# Handover: bippin

Last updated: 2026-07-06 19:51

*Source of truth: `handover_bippin.json`*


## Task
Fixed four critical bugs in transcript capture, token truncation, plan preservation, and max_tokens enforcement that were causing handover LLMs to lose context, and confirmed output-side token limits are correctly implemented via API parameters.

## Discussion
The askr system had interconnected bugs in checkpoint.py's _build_transcript_text() that were stripping tool input context and blindly truncating transcript/handover text at arbitrary character counts ([:400], [:300], [:80], [:4000]), causing plan definitions and tool inputs to be severed before the handover LLM ever saw them. This session fixed all four issues: (1) capturing actual tool input in transcript text instead of collapsing to bare tool names, (2) removing all blind character-count truncation caps and sending full content, (3) preserving plan tool-call entries in the transcript window regardless of position while maintaining recency filtering for other entries, and (4) surfacing max_tokens truncation via stop_reason checking in the Claude API client instead of failing silently. The user also rejected any manual post-generation truncation of LLM outputs, requiring instead that token limits be enforced via max_tokens parameter on API calls; investigation confirmed this is already correctly implemented.

## Accomplishments
- [x] Removed blind character-count truncation ([:400], [:300], [:80], [:4000]) from checkpoint.py _build_transcript_text and existing_json embedding; now sends full content to handover LLM
- [x] Captured actual tool input for plan tool-calls (TaskCreate, TaskUpdate) in transcript text instead of collapsing to bare TOOL: {name}
- [x] Replaced blind entries[-60:] recency slice in read_transcript with filter that always retains plan-defining tool calls plus recency window for other entries
- [x] Added stop_reason checking in clients/claude.py _post_messages/call_claude to detect and log max_tokens truncation explicitly instead of failing silently
- [x] All 188 tests passing after changes; verified _is_plan_entry() correctly identifies TaskCreate/TaskUpdate tool calls

## Next Actions
1. Fix quota-trigger to wait for Stop-hook signal before launching companion session, matching _open_companion_session_for_trigger's context-trigger behavior (TaskId 5)
   *Why: Quota path in lifecycle.py _execute_trigger currently launches companion sessions without waiting for turn-completion signal, creating race conditions and context loss; context-trigger already has correct pattern*
2. Verify that stage-plan context is preserved through autonomous handover jobs (e.g., git save, test runner) that run after context-switch stops
   *Why: User confirmed that session continuity problem extends to autonomous jobs running between user interactions; when multi-step stage plan is interrupted mid-implementation, autonomous job has no knowledge of remaining stages*
3. Review lifecycle.py code-path reuse across trigger types (quota, context, idle) to eliminate semantic mismatches that caused idle trigger to be misannounced as quota emergency
   *Why: Root cause of false inactivity alerts and unwanted session auto-launches; idle semantics (user absence) differ fundamentally from quota/context semantics (resource exhaustion)*

## Decisions
- Idle trigger uses dedicated _checkpoint_idle_inactivity() function, not generic _execute_trigger() shared with quota/context triggers — Idle semantics (user absence from app) differ fundamentally from quota/context semantics (resource exhaustion); code-path reuse caused false announcements and unwanted session launches
- Voice broadcast fires only on emergency conditions (quota/context at 90%+), never per-turn — Per-turn announcements create spam and false urgency; emergencies are rare and warrant interruption
- ask CLI uses separate API key, not Claude Code's OAuth token — Keeps CLI and Claude Code authentication domains separate; prevents quota/cost confusion between interactive and CLI usage
- Token limits must be enforced via max_tokens parameter on API calls, not via post-generation truncation — Mindless truncation after generation wastes compute, loses semantic structure, and breaks LLM output integrity; enforcement at call time is cleaner and more predictable

## User-Rejected Approaches
- **Manual post-generation truncation of LLM outputs to fit context windows** — "Rejected; requires instead that token limits be enforced via max_tokens parameter on API calls" (domain: clients/claude.py, checkpoint.py)

## Files In Play
- `askr/session/checkpoint.py`
- `askr/clients/claude.py`

## Relational Files
- `askr/lifecycle.py` (imported_by): Contains _execute_trigger() and _open_companion_session_for_trigger() that need alignment on quota-trigger wait behavior
- `tests/test_checkpoint_merge.py` (tested_by): Validates checkpoint.py changes; all 188 tests passing
- `tests/test_checkpoint_emergency.py` (tested_by): Validates checkpoint.py changes; all 188 tests passing
