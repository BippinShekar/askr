# Handover: bippin

Last updated: 2026-07-09 13:25

*Source of truth: `handover_bippin.json`*


## Task
The askr system fixed critical transcript-truncation bugs in checkpoint.py that were stripping tool inputs and plan definitions before the handover LLM saw them, eliminated race conditions in lifecycle.py's quota and context triggers by synchronizing on Stop-hook signals, suppressed false-positive idle-trigger fires by tracking turn-start markers, fixed phantom-session warnings in companion-session handover, serialized voice output across independent processes to prevent garbled announcements, and updated the roadmap to reflect actual implementation state (Phase 3.17 auto-population, Phase 3.16 emergency-handover unification, Phase 4 P4-1 approval gate, Phase 5 test suite, Phase 7.1 audit findings).

## Discussion
The askr system had interconnected bugs in checkpoint.py's _build_transcript_text() that were stripping tool input context and blindly truncating transcript/handover text at arbitrary character counts ([:400], [:300], [:80], [:4000]), causing plan definitions and tool inputs to be severed before the handover LLM ever saw them. This was fixed across four commits. Additionally, lifecycle.py's quota-trigger path was launching companion sessions without waiting for turn-completion signals, creating race conditions where checkpoints could capture half-finished turns and voice announcements could fire mid-answer. This session extracted the context-trigger's wait logic into _wait_for_turn_to_finish() and reused it in the quota path, so both trigger types now block on the same authoritative Stop-hook signal before acting. The idle trigger was firing false positives during active turns because _last_turn_stop() only measured elapsed time since the PREVIOUS turn's Stop event; this session added turn-start markers (written by user_prompt_submit.py, mirroring stop.py's turn-stop pattern) and gated the idle trigger on _turn_currently_active() to suppress it while a reply is in flight. Finally, _open_companion_session() was unconditionally telling new sessions that a previous session was still running even when no live process existed; this was fixed to only make that claim when a live process is actually found. A separate architectural issue was discovered: speak()/speak_signature() in voice.py had zero synchronization across independent OS processes (daemon trigger thread, per-turn background handover's async "Done" ping, hook processes), causing concurrent `say` invocations to play on top of each other and garble into nonsense. A cross-process flock now serializes all spoken output, with speak_signature's prefix+body pair locked as one unit to prevent interleaving. All 188 tests passing; git history confirms nine commits addressing these issues. This session also updated the roadmap to reflect actual implementation state, resolving self-contradictions in Phase 4/5 approval gate claims and confirming auto-population of decisions.jsonl.

## Accomplishments
- [x] Updated roadmap.md to reflect actual implementation state: Phase 3.16 (Emergency Handover Fix) marked DONE, Phase 3.17 (Auto-populate decisions.md) marked DONE, Phase 4 P4-1 approval gate marked DONE, Phase 5 test suite count corrected to 188 tests, Phase 7.1 audit table updated with Formula/askr.rb fix status, Bash cross-repo boundary check confirmation, and guard test coverage findings
- [x] Removed webhook URL concern from Phase 7.1 audit table per user directive (webhook has been scrubbed and is no longer in use)
- [x] Resolved Phase 4/5 self-contradictions in roadmap by confirming approval gate exists and is invoked at session_start.py:403, writing task_approval_pending notification
- [x] Documented pre-launch implementation scope: all Phase 1-3 items complete, Phase 4 P4-1 approval gate complete, Phase 5 IDE popup gap (task_approval_pending/guard_warning handling) remains as genuine coming-next item

## Next Actions
1. Commit roadmap.md changes and decisions.jsonl/goals.jsonl entries to main branch
   *Why: Roadmap updates reflect actual implementation state and resolve release-blocking contradictions; decisions and goals entries document architectural choices made across recent sessions*
2. Restart daemon with `askr launch --restart` and verify voice/git-save timing under normal operation
   *Why: Recent voice serialization and lifecycle fixes need validation in live environment to confirm no regressions in announcement timing or checkpoint capture*
3. Implement Phase 5 IDE popup gap: add task_approval_pending and guard_warning case handlers to extension.js checkNotification()
   *Why: This is the only genuine pre-launch blocker remaining; all other Phase 1-5 items are complete or have documented workarounds*

## Decisions
- Both quota-trigger and context-trigger wait for Stop-hook signal before checkpointing or launching companion sessions — Eliminates race conditions where checkpoint could capture half-finished turns; authoritative turn-completion signal is the only safe synchronization point for trigger actions
- Idle trigger is suppressed while a turn is actively in progress via _turn_currently_active() gate; turn-start markers are written by user_prompt_submit.py and compared against most recent turn-stop marker — _last_turn_stop() only measures elapsed time since the PREVIOUS turn's Stop event and has no knowledge of whether a new turn has started; idle_secs would grow through an entire in-progress turn, firing false positives during normal thinking gaps. Turn-start markers provide authoritative signal of active user interaction.
- Abandoned turn-start markers (older than MAX_TURN_ACTIVE_SECS = 30 min with no matching stop) are treated as inactive rather than permanently blocking idle-checkpoint — Crashed or closed sessions should not permanently disable the idle-checkpoint safety net; 30 minutes is a reasonable upper bound for a single turn's processing time
- Companion-session handover only claims a previous session is still running when a live process is actually found; otherwise directs new session to pick up from Next Action directly — Unconditionally warning about phantom sessions that don't exist leaves new sessions deferring to non-existent work; the claim must be grounded in actual process detection
- All voice output across independent processes (daemon trigger thread, per-turn background handover async pings, hook processes) is serialized via cross-process flock to prevent concurrent `say` invocations from overlapping — Multiple independent OS processes call speak()/speak_signature() with no coordination; concurrent invocations play on top of each other and audibly garble into nonsense. A shared lock file ensures only one process speaks at a time, and speak_signature's prefix+body pair is locked as one atomic unit to prevent interleaving.

## User-Rejected Approaches
- **Manual post-generation truncation of LLM outputs to fit context windows** — "Rejected; requires instead that token limits be enforced via max_tokens parameter on API calls" (domain: clients/claude.py, checkpoint.py)

## Failed Approaches
- [2026-07-02] Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire — Semantic confusion between user-initiated turns and system-generated responses; required adding explicit turn-start markers to distinguish active user interaction from background processing
- [2026-07-04] Debouncing continuous per-turn checkpoints to reduce frequency while keeping the hook active — User rejected the entire continuous-checkpoint model; the problem is not frequency but the fundamental design of checkpointing on every turn, which blocks user interaction — User rejected the underlying model; frequency reduction does not address the core architectural issue
- [2026-07-04] Reusing `_execute_trigger()` for all three trigger types (quota, context, idle) — Idle conditions have different semantics than quota/context emergencies; code-path reuse caused misannouncement and unwanted session auto-launch — Idle trigger has fundamentally different semantics (background safety net vs. emergency response); shared code path caused incorrect behavior and false announcements
- [2026-07-06] Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds() — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire — Duplicate of 2026-07-02 failure; semantic confusion persisted until turn-start markers were added
- [2026-07-06] Reusing _execute_trigger() for all three trigger types (quota, context, idle) — Idle conditions have different semantics than quota/context emergencies; code-path reuse caused misannouncement and unwanted session auto-launch — Duplicate of 2026-07-04 failure; architectural separation required

## Files In Play
- `roadmap.md`

## Relational Files
- `askr/session/checkpoint.py` (configures): Roadmap documents implementation status of checkpoint.py features (transcript truncation fixes, plan tool-call preservation, handover LLM input integrity)
- `askr/session/lifecycle.py` (configures): Roadmap documents implementation status of lifecycle.py trigger semantics (quota/context/idle trigger synchronization, turn-start markers, phantom-session detection)
- `askr/clients/voice.py` (configures): Roadmap documents implementation status of voice.py cross-process serialization for speak() and speak_signature()
- `askr_state/decisions.jsonl` (imported_by): Roadmap references decisions.jsonl auto-population (Phase 3.17); this session added five new decision entries documenting architectural choices

## Uncommitted Files
- `askr_state/decisions.jsonl`
- `askr_state/goals.jsonl`
- `askr_state/handover_bippin.json`
- `askr_state/handover_bippin.md`
- `askr_state/implementation_bippin.jsonl`
- `roadmap.md`
