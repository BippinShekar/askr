# Stress Test: Overnight Portfolio Tetris Build

## Goal
Validate askr's full autonomous stack end-to-end on a real greenfield project that
is too large to complete in a single session.

## The Task
Transform Bippin's portfolio website into a Tetris-like experience:
- Portfolio pieces (projects, skills, experience) fall as Tetris blocks
- When blocks form a complete row, the row clears
- On clear, the user gets a new fact (about Bippin, a project, a skill)
- Full game loop: gravity, collision, line-clear, score, game over
- Must feel polished — not a gimmick, an actual portfolio someone would show off

## Why This Is a Good Stress Test
- Greenfield project: no existing code, Claude must plan and scaffold from scratch
- Multi-session by design: 3–6 sessions minimum (scaffold → game loop → rendering → content → polish)
- Overnight run: no human intervention, tests autonomous handover + continuation
- Quota boundary likely: if started evening, will hit quota reset mid-build
- Context switches: each session needs to correctly pick up from handover without re-doing work

## What Gets Validated

| Capability | Pass Condition |
|---|---|
| ctx trigger fires | New session opens when ctx hits 65% |
| Prompt auto-submits | Claude starts reading handover, not sitting blank at `>` |
| Handover quality | Next session continues from exact stopping point, no repeated work |
| Quota wait + resume | If quota resets overnight, daemon waits and auto-restarts |
| Goal tracking | askr goal persists across sessions, askr status shows active goal |
| Discord notifications | Accurate — "session resumed" only when session actually started |
| Morning state | `askr status` shows sessions run, work done, where it stopped |

## Pre-conditions Before Running
- [ ] Validate CR fix: watch this askr session hit 65% ctx, confirm auto-continuation submits and works
- [ ] Reload leaps Cursor window so extension is fresh
- [ ] `askr init` in portfolio repo
- [ ] Set a clear goal: `askr goal add "Build Tetris portfolio — blocks are projects/skills/experience, row-clear shows a new fact about me"`
- [ ] Confirm daemon is running: `askr status`
- [ ] Start Claude in portfolio repo and give it the brief (see below)

## Opening Brief for Claude
```
I want to transform this portfolio into a Tetris-like game.
Portfolio pieces (projects, skills, experience) fall as Tetris blocks.
When blocks form a complete row, the row clears and a new fact about me appears.
Full game loop: gravity, collision, line-clear, score, game over state.
Should feel polished — this is a real portfolio, not a toy.

askr is managing this session. Work autonomously. When you hit a ctx limit, askr
will save your handover and open a new session. Read the handover at the start of
each session and continue from the Next Action. Do not repeat completed work.
```

## Portfolio Repo
- Location: TBD (wherever Bippin's portfolio lives)
- Run: `askr init` there first

## Success Definition
Wake up to a working Tetris portfolio with no human intervention required overnight.
