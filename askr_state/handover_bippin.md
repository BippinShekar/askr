# Handover: bippin

Last updated: 2026-06-14 14:44

*Source of truth: `handover_bippin.json`*


## Task
Restructure roadmap phases: move approval gate to Phase 5, rename Phase 4 (Public Launch) to Phase 4 (Team Scale), push launch to Phase 7, and strip migration overhead since only single-user deployment currently.

## Discussion
User clarified that askr is currently single-user only, so migration complexity in Phase 4 was premature. Agreed to move approval gate (dangerously-skip-permissions, unrestricted Bash, rm/delete triggers) into Phase 5 (Hardening). Restructured Phase 4 from 'Public Launch' to 'Team Scale' with three stages: P4-0 (team directory structure), P4-1 (task queue per developer), P4-2 (askr team CLI). Public launch pushed to Phase 7. Two roadmap.md edits completed to reflect these changes.

## Accomplishments
- [x] Moved approval gate feature from Phase 7 into Phase 5 (Hardening) with trigger conditions and two-path behavior (IDE popup vs Discord headless)
- [x] Removed Phase 3.9 duplicate entry from roadmap
- [x] Renamed Phase 4 from 'Public Launch' to 'Team Scale' with three substages (P4-0, P4-1, P4-2) and removed migration overhead assumptions
- [x] Pushed public launch goals to Phase 7 (GitHub release, Twitter thread, external users, brew tap)

## In Progress
- `roadmap.md` (line 567): Phase 4 (Team Scale) structure incomplete — P4-2 (askr team CLI) section cut off mid-table at line 567

## Next Actions
1. Complete Phase 4 (Team Scale) roadmap section: finish P4-2 (askr team CLI) feature table and add P4-3 if needed, then add completion criteria ('Done when: ...')
   *Why: Roadmap edit was interrupted; Phase 4 structure is incomplete and needs closure before moving to next phase planning*
2. Commit the three roadmap.md changes to git with message: 'Restructure phases: approval gate→P5, P4→Team Scale (P4-0/P4-1/P4-2), launch→P7, strip migration overhead'
   *Why: Changes are tracked in implementation_state.md but not yet committed; git diff shows modifications that need to be persisted*
3. Review Phase 5 (Hardening) to confirm approval gate placement doesn't conflict with other hardening features and that it lands before Phase 7 task queuing ships
   *Why: User emphasized approval gate must be in place before task queuing (Phase 7) to prevent dangerous permissions from being inherited by queued tasks from other developers*
4. Update implementation_state.md to reflect that Phase 4 is now 'Team Scale' (not 'Public Launch') and Phase 7 is now 'Public Launch' (not task queuing)
   *Why: State tracking file needs to match the restructured roadmap to avoid confusion in future sessions*

## Decisions
- Approval gate moved to Phase 5 instead of Phase 7 — Phase 5's theme is 'Zero misfires. Trust is the product.' — approval gate belongs there, and it must ship before task queuing (Phase 7) to prevent dangerous permissions from being inherited by queued tasks
- Phase 4 renamed from 'Public Launch' to 'Team Scale' with substages P4-0, P4-1, P4-2 — Current single-user deployment doesn't need migration complexity; team scaling is the actual next phase after stress testing. Public launch deferred to Phase 7 when team features are stable
- Removed migration overhead from Phase 4 planning — User clarified askr is only used by them currently, so multi-user migration is not an immediate concern; can be added later if team adoption happens

## User-Rejected Approaches
- **Phase 7 should contain task queuing with migration overhead for multi-user deployments** — "there is no migration as of now, it's only me using it, so it won't be as much a ordeal as you imagine. Also, being phase 7 doesn't make sense, but must be phase 4" (domain: roadmap.md phases and feature placement)

## Failed Approaches
- Placed task queuing and team features in Phase 7 with migration complexity — User clarified single-user deployment makes migration premature; restructured to Phase 4 (Team Scale) with simpler substages

## Files In Play
- `roadmap.md`
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`

## Relational Files
- `askr_state/decisions.md` (configures): Records architectural decisions about phase structure and feature placement; should be updated to reflect Phase 4→Team Scale rename
- `askr_state/goals.md` (configures): Tracks open goals; 'Verify context checkpoint cards display correct turns remaining in staging' is still pending and may be affected by phase restructuring

## Uncommitted Files
- `askr_state/implementation_state.md`
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Phase 4 (Team Scale) roadmap section is incomplete — P4-2 feature table was cut off mid-edit and needs to be finished before commit
