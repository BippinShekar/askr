# Handover: bippin

Last updated: 2026-06-14 14:34

*Source of truth: `handover_bippin.json`*


## Task
Design approval gates and roadmap placement for collaborative session injection features in askr, with permission-based safety constraints

## Discussion
User's friend requested three bundled features: remote session control, task injection into others' sessions, and auto-run capabilities for team collaboration (50+ person team). Session focused on disaggregating these asks and determining feasibility. User then pivoted to asking where the remaining 3 features should be added to the roadmap, with critical constraint: approval gates must activate when users have dangerous permissions enabled (skip permissions, file deletion) because session-agnostic permissions compound risk. Roadmap was partially edited (Phase 4 removed, Phase 3.11 added) but discussion on placement and safety architecture was incomplete when session ended.

## Accomplishments
- [x] Disaggregated three bundled collaboration requests into distinct feasibility profiles
- [x] Identified that task injection is 80% feasible; remote control and auto-run have different risk/complexity profiles
- [x] Began roadmap restructuring (removed Phase 4, added Phase 3.11 JSON Handover Schema placeholder)

## In Progress
- `roadmap.md` (line 291): Determining which phase (3.x vs 4) to place: (1) task injection into others' sessions, (2) approval gate system for dangerous permissions, (3) session-agnostic permission model. Phase 4 was deleted but not replaced with new structure.
- `askr_state/decisions.md`: Safety architecture for approval gates: when to trigger, what permissions trigger them, how to prevent permission compounding across sessions

## Next Actions
1. Read full roadmap.md and decisions.md to understand current phase structure, then map the three collaboration features to appropriate phases with explicit safety gates
   *Why: User asked for phase placement but session ended before this analysis. Need full context to avoid conflicts with existing phase goals.*
2. Design approval gate trigger matrix: create a table mapping (permission type) × (action type) → (requires approval: yes/no). Include: skip permissions, file deletion, directory deletion, env var modification, network access.
   *Why: User explicitly flagged that dangerous permissions + session-agnostic model = compounding risk. This is a hard constraint for any collaboration feature.*
3. Propose Phase 3.12 or Phase 4 structure: (a) task injection with approval gates (Phase 3.12?), (b) session-agnostic permission model with safety constraints (Phase 3.13?), (c) remote control as Phase 4 stretch goal. Get user confirmation on phase numbering.
   *Why: Roadmap was partially edited but lacks clear phase boundaries. User needs to approve placement before implementation planning.*
4. Document the permission compounding problem: show concrete scenario (e.g., User A has skip=true, User B injects task into A's session, task runs with A's permissions, deletes files). Propose isolation strategy.
   *Why: This is the core safety blocker for collaborative features at 50-person scale. Must be solved before feature design.*
5. Commit roadmap.md and decisions.md changes with message: 'WIP: Roadmap restructure for collaboration features + approval gate design'
   *Why: Changes are uncommitted; need to preserve state for next session.*

## Decisions
- Disaggregate 'remote control' from 'task injection' and 'auto-run' — treat as three separate features with different risk profiles — Remote control is highest risk (real-time session hijacking); task injection is medium risk (async, auditable); auto-run is lowest risk (deterministic). Bundling them masks distinct tradeoffs.
- Approval gates must be permission-aware, not just action-aware — User flagged that session-agnostic permissions cause compounding risk. A task injected into a session with skip=true is fundamentally different from one with skip=false.

## Failed Approaches
- Treating 'remote control' as a single feature request — User's friend actually asked for three distinct things; conflating them prevented clear feasibility analysis and roadmap placement.

## Files In Play
- `roadmap.md`
- `askr_state/decisions.md`
- `askr_state/notifications.log`

## Relational Files
- `askr_state/permissions.md` (configures): Approval gate design depends on understanding current permission model and how it's enforced across sessions.
- `askr_state/session_schema.md` (configures): Task injection and session control features require understanding session state structure and isolation boundaries.
- `stress-tests/` (tested_by): Collaboration features at 50-person scale will need stress testing; current stress-tests/ directory should be reviewed for multi-session scenarios.

## Uncommitted Files
- `askr_state/notifications.log`
- `roadmap.md`
- `stress-tests/`

## Blockers
- Unclear phase structure after Phase 4 deletion — need to confirm whether collaboration features go in Phase 3.x (pre-launch) or Phase 4 (post-launch)
- Permission compounding risk not yet formally modeled — approval gate design cannot proceed without concrete threat scenarios
