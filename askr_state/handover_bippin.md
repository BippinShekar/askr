# Handover: bippin

Last updated: 2026-07-10 20:20

*Source of truth: `handover_bippin.json`*


## Task
Fixed test suite pollution and root-caused repeated voice announcements by patching incorrect mock targets and adding voice-log isolation; completed Phases 3.13 and 3.15 with user-rejection tracking and smart context injection.

## Discussion
The repeated voice announcements were caused by three independent bugs: quota trigger's dedup key was empty during fresh sessions (no reset_at yet), context trigger's companion flag was being wiped every 5 minutes instead of per-session-end, and the test suite itself was shelling out to real macOS `say` because it mocked the wrong voice function. All three are now fixed. Separately, Phases 3.13 (rejected-decision persistence) and 3.15 (smart context injection) were completed and verified against code. The test suite now runs in 5.5s instead of ~62s and produces zero pollution in voice_log.jsonl.

## Accomplishments
- [x] Fixed quota trigger re-announcement: dedup key now held empty until reset_at is known from API or checkpoint
- [x] Fixed context trigger companion-session flag: now pruned on liveness check instead of every Stop event, preventing 5-minute-cycle relaunches
- [x] Fixed test suite voice pollution: patched announce() directly instead of guessing internal dispatch targets; added _IsolatedVoiceLogMixin for logging isolation
- [x] Implemented voice_log.jsonl diagnostic infrastructure: every spoken-output attempt now logged with reason and source
- [x] Completed Phase 3.13 (user-rejection tracking): rejected_decisions.jsonl with append-only writes, file locking, substring dedup
- [x] Completed Phase 3.15 (smart context injection): targeted context replacement of full-dump-every-session behavior
- [x] Fixed Signal 3 (handover next_actions): now skips degraded fallback placeholders from failed generation
- [x] Fixed signal quality: automated checkpoint/idle commits no longer dilute commit-scope signal window

## Next Actions
1. Merge this PR to main once code review is complete
   *Why: All 289 tests passing, voice pollution eliminated, both roadmap phases verified and complete*
2. Monitor voice_log.jsonl in production for 48 hours post-merge to confirm zero re-announcement recurrence
   *Why: Three independent bugs fixed; want to verify no new edge cases emerge under real load*
3. Update CLAUDE.md guard directive to reflect Phase 3.13 rejected_decisions.jsonl checks
   *Why: Guard logic is already implemented and synchronized; documentation should match*

## Decisions
- Quota trigger dedup key must be non-empty before firing; hold off announcing until reset_at is known from API or checkpoint — Empty dedup key during fresh sessions or API hiccups caused re-announcement on every poll cycle; quota reset is a one-time event per window, not a recurring trigger
- Context trigger companion-session flag is pruned on liveness check (session still running), not on every Stop event — Pruning per-turn caused flag to reset every 5 minutes, triggering relaunches repeatedly as long as context stayed above threshold; pruning on liveness preserves the flag across the session's lifetime
- Test suite patches announce() directly instead of guessing which internal voice dispatch target applies — announce() dispatches to speak() OR speak_signature() depending on load_voice_mode(); patching only speak() left speak_signature() unpatched, causing real macOS `say` calls on machines with voice_notifications enabled
- Signal 3 (handover next_actions) skips degraded fallback placeholders (generic 'review manually' text) that were being accepted as confident 0.85 directions despite failed handover generation — Fallback text is a sentinel for failed generation, not a real next step; accepting it masks the failure and feeds garbage direction to the next session
- Phase 3.13 S2–S5 (user-rejection tracking) persists rejected decisions to rejected_decisions.jsonl with append-only writes, file locking, and substring dedup on what_was_proposed — Mirrors the established pattern from decisions.jsonl and failed_approaches.jsonl; append-only + locking prevents concurrent-write corruption; substring dedup prevents duplicate entries while allowing confidence updates
- Phase 3.13 S5 (CLAUDE.md guard directive) is kept byte-for-byte synchronized with askr/cli/askr.py template so future askr init runs report 'unchanged' — Prevents accidental divergence between the documented guard behavior and the actual template; idempotent init runs are a quality signal

## Failed Approaches
- Patching askr.clients.voice.speak in test_context_cut_handover.py and test_quota_trigger_writes_quota_notification to prevent real speech — stop.py calls announce(), which dispatches to either speak() or speak_signature() depending on load_voice_mode(); patching only speak() left speak_signature() unpatched, so real macOS `say` subprocess calls still fired on machines with voice_notifications enabled
- Not redirecting voice._VOICE_LOG_PATH in test_voice.py's SpeakGatingTests/SpeakSignatureTests — Even with subprocess.run mocked (no real speech), every test run wrote real fixture entries into ~/.config/askr/voice_log.jsonl, polluting the diagnostic log that feature exists to make debugging trustworthy

## Files In Play
- `tests/test_context_cut_handover.py`
- `tests/test_voice.py`
- `askr/clients/voice.py`
- `askr/cli/stop.py`
- `askr/checkpoint.py`
- `askr/reader.py`
- `askr/guard.py`

## Relational Files
- `askr/clients/voice.py` (imports): Core voice module; announce() dispatch logic and voice_log.jsonl writes
- `askr/cli/stop.py` (imported_by): Calls announce() for quota and context triggers; behavior depends on voice dispatch routing
- `askr/checkpoint.py` (imported_by): Persists rejected_decisions.jsonl; Phase 3.13 implementation
- `askr/reader.py` (imported_by): Smart context injection; Phase 3.15 implementation
- `askr/guard.py` (imported_by): Checks rejected_decisions.jsonl; Phase 3.13 guard filtering
- `askr/cli/askr.py` (configures): CLAUDE.md template must stay byte-for-byte synchronized with guard directive
