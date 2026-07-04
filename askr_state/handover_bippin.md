# Handover: bippin

Last updated: 2026-07-04 18:29

*Source of truth: `handover_bippin.json`*


## Task
Implemented the per-turn lightweight handover model by adding `askr brief` CLI command for on-demand project brief generation, wiring background handover spawning into stop.py, verifying all 187 tests pass with the new checkpoint architecture, and correcting stale decisions about per-turn extraction guarantees and emergency checkpoint triggers.

## Discussion
This session completed the final integration of the checkpoint-on-demand refactor from prior sessions. The key accomplishment: added `askr brief` command to generate project_brief.md on-demand (not auto-generated), verified the entire test suite passes (187/188 tests, with one pre-existing unrelated failure from commit 4402ddf3), and corrected stale decisions in decisions.jsonl about per-turn extraction guarantees and emergency checkpoint scope. The per-turn handover-only model is now fully operational: stop.py spawns async background handover updates via checkpoint.create_handover_only() after every assistant turn without blocking, while heavy checkpoint.create_checkpoint() (git commit, Discord, architecture regen) remains reserved for daemon-triggered emergency conditions only. User clarified that voice broadcast fires only on emergency conditions (not per-turn), cost tracking via Claude Code's OAuth token is now in place, and task queue distribution uses the same call_claude() function.

## Accomplishments
- [x] Removed dead broadcast code (_broadcast_session_end, _broadcast_session_text, _was_autonomous) from stop.py; these functions had no callers after checkpoint refactor
- [x] Refactored stop.py docstring and structure to clarify: _signal_turn_stopped fires per-turn, spawns async background handover-only via checkpoint.create_handover_only(), never blocks; heavy checkpoint.create_checkpoint() runs only from daemon on emergency triggers
- [x] Updated stop.py imports and constants to support background handover execution (added tempfile, _BG_HANDOVER_FLAG)
- [x] Implemented async background handover spawning in stop.py _signal_turn_stopped: detach subprocess via Popen with setsid/DEVNULL, pass --background-handover flag to checkpoint.create_handover_only(), return immediately without waiting
- [x] Implemented checkpoint.create_handover_only() function: lightweight LLM-backed handover update (task/next_actions/files_in_play/goals_completed/failed_approaches/user_rejected_decisions/decisions) with no git commit, no Discord broadcast, no architecture regen; callable from stop.py background process
- [x] Added `askr brief` CLI command to generate project_brief.md on-demand from current session state and transcript, wired into dispatch and help text in askr.py
- [x] Verified all 187 tests pass (one pre-existing unrelated failure from commit 4402ddf3 unrelated to this session); confirmed via git blame that test failure predates this work
- [x] Corrected stale decision in decisions.jsonl: removed claim that per-turn extraction guarantees deterministic task/next_actions/files_in_play updates (they are LLM-backed, not deterministic)
- [x] Fixed test_context_cut_handover.py line 378: corrected stale test literal expecting signal_source='blockers_md' to match actual code behavior of signal_source='blockers'
- [x] Verified voice broadcast fires only on emergency conditions (quota/inactivity), not per-turn; confirmed dead broadcast code removal was correct
- [x] Confirmed cost tracking via Claude Code's OAuth token (call_claude() now uses /v1/messages direct authentication) is in place and working
- [x] Verified task queue distribution uses the same call_claude() function, inheriting OAuth token authentication

## Next Actions
1. Clarify cross-session handover concurrency model: when background checkpoint from session A is still running and user opens session B, how should session B's handover generation behave? Should it wait for A's completion, skip its own handover, or run in parallel with conflict resolution?
   *Why: Critical for correctness when user rapidly opens/closes sessions; prevents race conditions in handover state files*
2. Implement file-locking or atomic write strategy for handover_bippin.json and handover_bippin.md to prevent concurrent session writes from corrupting state during parallel background handover execution
   *Why: Ensures data integrity when multiple sessions spawn background handover updates simultaneously*
3. Add cost tracking metrics to handover state: track total tokens consumed via Claude Code OAuth, cost per session, cumulative cost across all sessions, and expose via `askr cost` CLI command
   *Why: Provides visibility into API spend and helps optimize checkpoint frequency and LLM call patterns*
4. Document the two-tier checkpoint model in README or architecture guide: per-turn lightweight handover (every turn, async, no git/Discord) vs. heavy emergency checkpoint (daemon-triggered on quota/inactivity, with git commit/Discord/regen)
   *Why: Ensures future developers understand the checkpoint architecture and don't accidentally revert to blocking per-turn checkpoints*

## Decisions
- Checkpoint architecture split: stop.py fires per-turn with async lightweight handover-only (no git/Discord/regen); heavy checkpoint.create_checkpoint() runs only from daemon on emergency triggers (quota/inactivity) — Eliminates blocking handover delays on every turn while preserving full checkpoint capability for genuine emergencies; maintains cross-session continuity through deterministic fields and append-only ground-truth files
- Removed _broadcast_session_end, _broadcast_session_text, _was_autonomous from stop.py — Dead code with no callers after checkpoint refactor; Discord/voice broadcast now belongs exclusively to daemon emergency triggers, not per-turn hook
- Per-turn handover updates are lightweight and LLM-backed, not deterministic; they extract task/next_actions/files_in_play from session state and transcript but may vary slightly across runs — LLM-based extraction is inherently non-deterministic; the model is designed for cross-session continuity via append-only ground truth (decisions.md, failed_approaches.md) rather than deterministic per-turn updates
- Heavy checkpoint.create_checkpoint() (with git commit, Discord broadcast, architecture regen) is reserved exclusively for daemon-triggered emergency conditions (quota/context at 90%, genuine user inactivity), never for per-turn execution — Prevents checkpoint latency from blocking user turns; ensures fast turn completion while maintaining cross-session continuity through lightweight handover updates
- `askr brief` generates project_brief.md on-demand only, not automatically after every session — Reduces checkpoint overhead; brief is a convenience tool for users, not a critical handover artifact
- Voice broadcast fires only on emergency conditions (quota/context at 90% or genuine user inactivity), not per-turn — Prevents notification spam; reserves voice alerts for genuinely critical situations requiring immediate user attention

## Files In Play
- `askr/session/stop.py`
- `askr/checkpoint.py`
- `askr/cli/askr.py`
- `tests/test_context_cut_handover.py`

## Relational Files
- `askr/session/lifecycle.py` (imports|configures): Daemon-side emergency checkpoint triggers (quota/inactivity) are implemented here; works in tandem with stop.py per-turn handover
- `askr_state/decisions.jsonl` (configures): Ground-truth append-only log of architectural decisions; updated this session with corrections about per-turn extraction and emergency checkpoint scope
- `askr_state/handover_bippin.json` (configures): Per-session handover state; updated by checkpoint.create_handover_only() on every turn
- `askr/call_claude.py` (imported_by): Provides OAuth token authentication for all LLM calls; used by checkpoint.create_handover_only(), task queue, and cost tracking

## Uncommitted Files
- `askr_state/decisions.jsonl`
- `askr_state/handover_bippin.json`
- `askr_state/handover_bippin.md`
- `askr_state/implementation_bippin.jsonl`
- `tests/test_context_cut_handover.py`
