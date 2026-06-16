# Handover: bippin

Last updated: 2026-06-16 13:44

*Source of truth: `handover_bippin.json`*


## Task
Identified architectural requirements for multi-developer task assignment and auto-drain workflow; clarified shared vs. unique file structure and blocking semantics.

## Discussion
User rejected the explicit `askr task {dev-name} "do this"` workflow as wasteful of conversational turns. Instead, user wants inline task assignment during discussion (e.g., "let's make sure lochan takes care of Z") with automatic inference of assignee and task content from context. Session ended mid-design: user is asking for clarification on (1) how tasks get assigned implicitly, (2) how auto-drain works post-pull, (3) whether blockers.md is dev-specific, and (4) the overall approach for task routing and inference.

## Accomplishments
- [x] Confirmed Stage 1–4 shipped: conflict-free .gitattributes, askr init, task queue, and team commands
- [x] Identified user's rejection of explicit task syntax in favor of inline, context-aware assignment

## In Progress
- `askr/cli/askr.py`: Design task assignment inference engine and auto-drain post-pull logic
- `askr_state/blockers.md`: Clarify whether blockers are dev-specific or shared; design structure

## Next Actions
1. Design and document the task inference engine: how Claude Code will extract assignee (e.g., 'lochan') and task description from conversational context without explicit `askr task` syntax. Define the prompt/heuristic that identifies task boundaries.
   *Why: User explicitly rejected manual task syntax; inference is the core blocker for the desired workflow.*
2. Design auto-drain mechanism: define how tasks in `tasks/queue_{dev}.md` are automatically drained (moved to current_task or completed) when that dev pulls the repo. Decide: does drain happen on git pull hook, on next `askr` command, or on session start?
   *Why: User asked 'how are these tasks going to get auto-drained post pull?' — this is unresolved and critical for the workflow.*
3. Clarify blockers.md structure: decide if blockers are dev-specific (one per dev) or shared (one global file). If dev-specific, create `blockers_{dev}.md` pattern; if shared, define merge/conflict strategy.
   *Why: User asked 'blockers.md will be basically dev specific right?' — needs explicit design decision and file structure.*
4. Build a Stage 5 commit: implement task inference hook in Claude Code integration (or as a CLI command) that parses conversation context and auto-queues tasks for teammates.
   *Why: Inference engine is the missing piece to enable the desired 'inline assignment' workflow.*
5. Document the full multi-dev workflow in README or DESIGN.md: shared files (repo code), unique files (queue/current/blockers per dev), task flow (inline → queue → current → done), and auto-drain timing.
   *Why: User needs clarity on the complete system before implementation; documentation will unblock design decisions.*

## Decisions
- Task assignment must be inferred from conversational context, not explicit CLI syntax. — User rejected `askr task {dev-name}` as wasteful; wants inline assignment during discussion.

## User-Rejected Approaches
- **Explicit task syntax: `askr task {dev-name} "do this"` for assigning work to teammates.** — "I wouldn't want to waste one conversational turn with claude just to say assign this to lochan. I would instead do something like, while talking about xyz, let's make sure lochan takes care of z." (domain: askr/cli/askr.py and task assignment workflow)

## Files In Play
- `askr/cli/askr.py`
- `askr_state/tasks/queue_bippin.md`
- `askr_state/tasks/queue_lochan.md`
- `askr_state/blockers.md`
- `askr_state/current_task_bippin.md`
- `askr_state/current_task_lochan.md`

## Relational Files
- `askr/hooks/session_start.py` (configures): Session start hook will trigger auto-drain of queued tasks when dev pulls repo.
- `.gitattributes` (configures): Union merge strategy on append-only task queue files prevents conflicts across devs.

## Uncommitted Files
- `askr_state/notifications.log`

## Blockers
- Task inference engine design not yet specified: how does Claude Code extract assignee and task from conversation?
- Auto-drain timing undefined: when do queued tasks move to current_task or complete?
- Blockers.md structure unresolved: dev-specific or shared?
