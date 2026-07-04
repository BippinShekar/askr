# Handover: bippin

Last updated: 2026-07-04 17:54

*Source of truth: `handover_bippin.json`*


## Task
Designed checkpoint-on-demand architecture with emergency-only triggers (90% session quota, user inactivity timeout) and async background execution to eliminate blocking handover delays, while clarifying that handover continuity depends only on task/next_actions/files_in_play fields with opportunistic inference from other metadata.

## Discussion
Session resolved the architectural model for checkpoint-on-demand: checkpoints fire only in two emergency cases (session quota at 90%, user inactivity after N minutes), executed asynchronously via background subprocess to avoid blocking user interaction. User corrected a misunderstanding about handover continuity — the ground truth for cross-session continuity is task/next_actions/files_in_play (deterministic), while goals-completed, failed_approaches, user_rejected_decisions, and decisions are opportunistically extracted from the same checkpoint call with no guarantee they populate every turn. This distinction means the append-only ground-truth files (decisions.md, failed_approaches.md, etc.) are the actual continuity source, not the handover JSON fields. Cross-session concurrency when a background checkpoint is still running remains an open design question requiring clarification before implementation.

## Accomplishments
- [x] Clarified handover continuity model: task/next_actions/files_in_play are deterministic continuity fields; goals-completed, failed_approaches, user_rejected_decisions, decisions are opportunistic inference with no per-turn guarantee
- [x] Confirmed stop.py architecture: _signal_turn_stopped fires after every assistant turn; checkpoint-on-demand must be emergency-only, not continuous

## In Progress
- `None`: Design checkpoint-on-demand trigger system: 90% quota hard-limit + inactivity timeout (N minutes configurable), with async background execution (Popen + setsid/DEVNULL) to avoid blocking user interaction; coupled with voice announcement and Discord update

## Next Actions
1. Clarify cross-session handover concurrency model: when background checkpoint is still running in session A and user opens session B, how should session B's handover generation interact with session A's in-flight checkpoint? (block, merge, ignore, queue?) — this is a prerequisite for implementation
   *Why: User's question 'how will those background handover sessions be handled?' remains unresolved; architectural decision required before writing code*
2. Implement 90% quota trigger in stop.py: detect when session token budget reaches 90%, fire checkpoint async via Popen with setsid and DEVNULL, return immediately without blocking
   *Why: First concrete emergency trigger; user confirmed this is a legitimate checkpoint case*
3. Implement inactivity timeout trigger in stop.py: track last user message timestamp, checkpoint if no user input for N minutes (configurable, suggest 5-10 min), async execution same as quota trigger
   *Why: Second emergency trigger; user confirmed this is legitimate; coupled with voice announcement + Discord update per user spec*
4. Remove or disable the continuous per-turn checkpoint logic currently in stop.py (_signal_turn_stopped hook that fires after every assistant turn)
   *Why: User explicitly rejected continuous checkpointing; checkpoints must be emergency-only, not continuous*
5. Add voice announcement + Discord notification when checkpoint is triggered (both quota and inactivity cases)
   *Why: User specified this in the emergency-trigger spec; keeps user informed of background work*

## Decisions
- `speak()` function skips subprocess call when text is empty — Prevents spurious `say ""` calls that waste system resources; aligns with the settled decision that empty strings are valid skip signals
- Route all spoken announcements through unified `announce()` function instead of direct `speak()` calls — Centralizes voice configuration, ensures consistent voice selection, and simplifies future voice-related changes
- Default single-voice mode to Zarvox instead of Samantha — User preference; Zarvox provides better voice quality for announcements
- Guard `speak()` function against empty text messages with early return — Prevents spurious subprocess calls and subprocess errors when announcement text is empty
- Checkpoint-on-demand fires only in two emergency cases: (1) session quota at 90%, (2) user inactivity after N minutes — User explicitly rejected continuous per-turn checkpointing; checkpoints must be emergency-only to avoid blocking handover delays and unnecessary state writes
- Handover continuity depends deterministically on task/next_actions/files_in_play fields; goals-completed, failed_approaches, user_rejected_decisions, decisions are opportunistically extracted with no per-turn guarantee — Append-only ground-truth files (decisions.md, failed_approaches.md, etc.) are the actual continuity source; handover JSON fields are inference, not authoritative

## User-Rejected Approaches
- **Continuous checkpoint after every assistant turn (per-turn checkpointing via _signal_turn_stopped hook)** — "the checkpoint must only be run during emergency handover situations, ie. only one probable cases ever: (1) Session limit is at 90%, (2) When the user is inactive for whatever time" (domain: stop.py, checkpoint architecture)

## Failed Approaches
- Debouncing continuous per-turn checkpoints to reduce frequency while keeping the hook active — User rejected the entire continuous-checkpoint model; the problem is not frequency but the fundamental design of checkpointing on every turn, which blocks user interaction

## Files In Play
- `askr/stop.py`
- `askr/checkpoint.py`
- `.claude/settings.json`

## Relational Files
- `askr/checkpoint.py` (imported_by): create_checkpoint() is called by stop.py; contains the handover generation logic that must be backgrounded
- `.claude/settings.json` (configures): Defines Stop hook timeout and behavior; checkpoint-on-demand must respect these settings
- `askr/state/writer.py` (imported_by): file_lock() is used by checkpoint.py for atomic state writes; relevant to async checkpoint execution

## Uncommitted Files
- `askr_state/implementation_bippin.jsonl`

## Blockers
- Cross-session handover concurrency model undefined: when background checkpoint is still running in session A and user opens session B, the interaction pattern (block, merge, ignore, queue) must be specified before implementation can proceed
