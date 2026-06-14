# Handover: bippin

Last updated: 2026-06-14 14:38

*Source of truth: `handover_bippin.json`*


## Task
Integrate approval gate for queued tasks into Phase 5 roadmap and restructure Phase 7 for team-scale concurrent session management.

## Discussion
User's friend requested remote control + task injection features for 50-person team collaboration. After analysis, three distinct asks were identified: task injection (80% feasible), session control (complex), and permission-aware queuing (critical safety). User decided to focus on approval gate placement and roadmap restructuring. Approval gate must trigger when dangerous permissions (`--dangerously-skip-permissions`, unrestricted Bash, file deletion) are enabled, blocking queued task execution until confirmed. Phase 7 was restructured to address team-scale state management: flat file layout breaks at 50 devs, so new team-scoped directory structure with migration path was added as prerequisite stage P7-0.

## Accomplishments
- [x] Moved approval gate feature into Phase 5 (Hardening) with full specification: trigger conditions, behavior, and implementation tasks
- [x] Removed duplicate Phase 3.9 entry from roadmap
- [x] Restructured Phase 7 to add Stage P7-0 (team directory structure + migration) as prerequisite for concurrent session management
- [x] Defined new team-scoped directory layout with `teams/<team>/members/<dev>/` structure to handle 50+ developer concurrent writes

## In Progress
- `/Users/bippin/Desktop/askr/roadmap.md` (line 523): Phase 7 Stage P7-1 (task queuing) was being drafted but cut off mid-section. Needs completion after P7-0 definition.

## Next Actions
1. Complete Phase 7 Stage P7-1 specification: task queue storage format, task injection API, conflict resolution for concurrent queue writes, and implementation checklist
   *Why: P7-0 structure is defined but P7-1 (actual task queuing) was truncated. This is the core feature the user's friend wants to use tomorrow.*
2. Add Phase 7 Stage P7-2: session handoff + approval confirmation flow (IDE popup for Cursor, Discord notification for headless, task list + permission state display)
   *Why: Approval gate logic is in Phase 5, but the UX for confirming queued tasks needs explicit stage in Phase 7 to avoid scope creep.*
3. Commit roadmap.md changes with message: 'Phase 5: add approval gate for queued tasks; Phase 7: restructure for team-scale with P7-0 directory migration'
   *Why: Three files modified but not committed. Checkpoint before next session to avoid merge conflicts.*
4. Create `askr migrate` implementation task in Phase 7 P7-0 checklist: script to move existing flat `handover_<dev>.md` files into new `teams/<team>/members/<dev>/` layout without data loss
   *Why: User has existing project state; migration path is critical for adoption at 50-person scale.*
5. Verify Phase 5 approval gate does not conflict with Phase 3.8 (permission grants). Document that Phase 3.8 grants are session-scoped, not task-scoped, so approval gate is necessary even if user already granted permissions.
   *Why: User flagged this concern explicitly: permissions granted for user's own work should not auto-authorize someone else's queued task.*

## Decisions
- Approval gate belongs in Phase 5 (Hardening), not Phase 7 (Team Collaboration) — Gate must be in place before task queuing ships; Phase 5's theme is 'zero misfires, trust is the product.' Approval gate is a trust mechanism.
- Approval gate is askr-level check, not delegated to Claude Code permission prompts — `--dangerously-skip-permissions` bypasses Claude Code's own safety prompts entirely, so askr must enforce the gate independently.
- Team-scoped directory structure (P7-0) is prerequisite for Phase 7, not optional — Flat file layout (`handover_<dev>.md` × 50 in one dir) is unnavigable and causes concurrent write conflicts. Cannot ship team features without this.
- Approval gate triggers on any one of three conditions: dangerous permissions flag, unrestricted Bash tool, or file deletion patterns — Any single condition is sufficient to require confirmation; using OR logic ensures no dangerous state slips through.

## Files In Play
- `/Users/bippin/Desktop/askr/roadmap.md`

## Relational Files
- `/Users/bippin/Desktop/askr/askr_state/decisions.md` (configures): Approval gate decision should be logged here for future reference and team alignment.
- `/Users/bippin/Desktop/askr/askr_state/implementation_state.md` (imported_by): Tracks in-progress edits; already has entries for roadmap.md modifications this session.

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Phase 7 Stage P7-1 specification incomplete (cut off mid-draft). Cannot finalize Phase 7 structure until task queuing API is defined.
