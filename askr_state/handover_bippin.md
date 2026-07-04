# Handover: bippin

Last updated: 2026-07-04 17:47

*Source of truth: `handover_bippin.json`*


## Task
Designed checkpoint-on-demand architecture to replace continuous stop-hook execution, establishing emergency-only triggers (90% session quota, user inactivity timeout) with background async execution to eliminate blocking handover delays.

## Discussion
Session clarified that stop-hook checkpointing must be emergency-only, not continuous. User rejected the original design (checkpoint after every turn) and established two legitimate triggers: (1) session quota at 90%, (2) user inactivity timeout. The key architectural insight is that backgrounding the checkpoint via async subprocess eliminates the 30+ second blocking wait, making the feature viable without shifting project-brief or architecture-regen to per-session. Cross-session handover continuity when a background checkpoint is still running remains an open design question — needs clarification on how concurrent sessions handle in-flight handover state.

## In Progress
- `None`: Design checkpoint-on-demand trigger system: 90% quota hard-limit + inactivity timeout, with async background execution to avoid blocking user interaction

## Next Actions
1. Clarify cross-session handover continuity model: when background checkpoint is still running in session A and user opens session B, how should session B's handover generation interact with session A's in-flight checkpoint? (block, merge, ignore, queue?)
   *Why: User's question 'how will those background handover sessions be handled?' is unresolved; architectural decision required before implementation*
2. Implement 90% quota trigger in stop.py: detect when session token budget reaches 90%, fire checkpoint async (Popen with setsid/DEVNULL), return immediately without blocking
   *Why: First concrete emergency trigger; user confirmed this is a legitimate checkpoint case*
3. Implement inactivity timeout trigger: track last user message timestamp, checkpoint if no user input for N minutes (configurable, suggest 5-10 min), async execution same as quota trigger
   *Why: Second emergency trigger; user confirmed this is legitimate; coupled with voice announcement + Discord update per user spec*
4. Remove or disable the continuous per-turn checkpoint logic currently in stop.py (the _signal_turn_stopped hook that fires after every assistant turn)
   *Why: User explicitly rejected this design; checkpoints must be emergency-only, not continuous*
5. Add voice announcement + Discord notification when checkpoint is triggered (both quota and inactivity cases)
   *Why: User specified this in the emergency-trigger spec; keeps user informed of background work*

## Decisions
- `speak()` function skips subprocess call when text is empty — Prevents spurious `say ""` calls that waste system resources; aligns with the settled decision that empty strings are valid skip signals
- Route all spoken announcements through unified `announce()` function instead of direct `speak()` calls — Centralizes voice configuration, ensures consistent voice selection, and simplifies future voice-related changes
- Default single-voice mode to Zarvox instead of Samantha — User preference; Zarvox provides better voice quality for announcements
- Guard `speak()` function against empty text messages with early return — Prevents spurious subprocess calls and subprocess errors when announcement text is empty
- Cross-repo Claude Code session switching is an open gap not solved by upstream tooling and is a potential feature for askr — Claude Code locks `.claude/` config to session-start directory; switching between repos requires manual workaround; askr could address this
- Checkpoints must be emergency-only, triggered only on 90% session quota or user inactivity timeout, never continuously after every turn — User rejected continuous checkpointing; 30+ second blocking waits are unacceptable UX; emergency-only + async backgrounding solves the problem without shifting project-brief or architecture-regen to per-session
- Background checkpoint execution via async subprocess (Popen with setsid/DEVNULL) to avoid blocking user interaction — Eliminates the 30+ second wait for handover generation; user can continue texting or open new session while checkpoint runs in background

## User-Rejected Approaches
- **Continuous checkpoint execution after every assistant turn (current stop.py behavior with _signal_turn_stopped)** — "the checkpoint must only be run during emergency handover situations, ie. only one probable cases ever: (1) Session limit at 90%, (2) User inactive for X time" (domain: stop.py, checkpoint trigger logic)
- **Shift project-brief regeneration or architecture-regen to per-session or on-demand basis to avoid blocking** — "that can either be done like that, or via project brief regen being shifted to per session... and architecture regen we will take care of when we are building it" (domain: checkpoint architecture, project-brief generation strategy)

## Failed Approaches
- [2026-07-02] Attempting to fix handover generation by filtering git status output at the point of collection — Root cause was deeper: _get_uncommitted_files() was not filtering .claude/ directory at all; needed explicit exclusion logic
- [2026-07-02] Storing project root in global ~/.config/askr/config.json as direct fix for nested worktree lockout — This recreates the fallback contamination bug that was just fixed (get_state_dir() loading a different project's path); requires project-local storage instead, but that conflicts with current guard strategy until cross-repo execution model is clarified
- [2026-07-02] Attempted to fix nested worktree lockout by storing absolute project root in config.json and using it for guard validation — Conflicts with desired architecture supporting multi-repo concurrent execution; direct implementation would block legitimate cross-repo task spawning
- [2026-07-02] Implementing project-root-based path locking to prevent nested worktree cwd-drift lockout — Conflicts with desired architecture: system must support multi-repo concurrent execution from single terminal, which requires cross-repo execution guards to be permissive rather than restrictive
- [2026-07-02] Treating any entry with 'type': 'user' as a real user message in _turn_elapsed_seconds — Tool_result entries also have 'type': 'user' but represent system responses, not user input; this caused the gate to almost never fire

## Files In Play
- `/Users/bippin/Desktop/askr/stop.py`
- `/Users/bippin/Desktop/askr/.claude/settings.json`

## Relational Files
- `/Users/bippin/Desktop/askr/stop.py` (configures): Contains stop-hook logic and checkpoint trigger implementation; needs emergency-only trigger refactor
- `/Users/bippin/Desktop/askr/.claude/settings.json` (configures): Defines stop-hook timeout and execution settings; may need adjustment for async backgrounding

## Blockers
- Cross-session handover continuity model undefined: when background checkpoint is running in session A and user opens session B, how should they interact?
