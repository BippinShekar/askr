# ASKR

# Autonomous Session Orchestration Layer For Claude Code

---

# Mission

Askr exists to solve two problems that happen simultaneously when building with Claude Code:

1. Sessions exhaust — context fills, quota runs out, work stops
2. Teams drift — one developer doesn't know what the other built

Both problems share one solution: structured, persistent project state that Claude always knows about, that git always tracks, and that any session can resume from.

> Claude may stop. Work must not.
> Your co-founder may sleep. Context must not be lost.

---

# What Askr Is

A session orchestration daemon for Claude Code that:

- Monitors context fill and quota burn rate simultaneously
- Intercepts before Claude auto-compacts (which is lossy)
- Checkpoints cleanly and resumes automatically
- Maintains project state files that both developers share via git
- Reports what happened while you were gone

Not a chatbot. Not a wrapper. Not a Claude replacement.

A reliability layer that makes Claude Code viable for serious, long-horizon work between two people.

---

# What Already Exists

The `ask` CLI — already built, already working:

```bash
ask "cto: best way to structure the auth layer?"
ask "debug: getting a 401 on every login attempt"
ask "ceo: should we build this or buy?"
```

This is a fast, low-token Q&A tool over your codebase using Claude Haiku or OpenAI.

Its role within Askr: **the fallback layer during quota resets.**

When Claude Code quota is exhausted and you're waiting for reset, `ask` answers architectural and debugging questions grounded in the project snapshot. No wasted time. No context switching.

---

# The Two Problems In Detail

## Problem 1: Session Exhaustion

Claude Code has two simultaneous limits:

**Context window** (~200k tokens default)
- Fills up as the session grows
- When full, Claude auto-compacts — lossy, retains ~20-30% of details
- Quality degrades before this: circular reasoning starts at 20% fill, forgotten decisions at 40%

**5-hour quota window** (per plan tier)
- Rolling window from first message
- Burns at variable rate depending on task complexity
- In March 2026, single prompts consumed 3-7% of session quota
- Max 20x plans exhausted in under 70 minutes

Both limits end the same way: Claude stops mid-task. Context is lost. Recovery is manual and painful.

---

## Problem 2: Team Drift

Two co-founders building the same product with Claude Code:

```
Dev A works until 11pm
↓
Dev B opens Claude at 9am
↓
Claude knows nothing about last night
↓
Dev B asks Dev A on Slack
↓
Dev A explains. Again.
```

This is not a communication problem. It's a state problem.

The fix: project state committed to git, read automatically at every session start. Git becomes the communication layer. Claude already knows what your co-founder did.

---

# The Two Triggers

Askr has two distinct intervention points. Not one.

---

## Trigger A: Context Window Near Compaction (~90%)

```
Context approaching auto-compact threshold
↓
Askr intercepts BEFORE Claude compacts
↓
Writes handover.md (complete, structured)
↓
Stops current session cleanly
↓
Immediately starts new session (no waiting)
↓
New session reads handover.md
↓
Claude continues from exact next step
```

**Why intercept instead of letting Claude compact?**

Claude's auto-compact is lossy — it summarises everything and discards ~70-80% of detail. Askr's handover.md captures 100% of what matters in a structured format Claude can act on immediately.

This can happen multiple times inside a single 5-hour quota window.

No downtime. Just a clean context reset.

---

## Trigger B: Quota Running Low

```
5-hour window quota running low
↓
Askr checkpoints properly
↓
Writes handover.md
↓
Updates all state files
↓
Git commit + push
↓
Stops current session
↓
Waits for quota reset
  (exact time: window start + 5 hours, from JSONL timestamp)
↓
Auto-launches new session after reset
↓
New session reads handover.md
↓
Claude continues from exact next step
```

This is the overnight scenario. Deterministic — Askr knows exactly when the window resets.

---

## What 50% Means

50% context fill is **not a stop trigger**.

It is a StatusLine signal:

```
Askr ⚠  ctx:50%  quota:71%
```

Developer sees it. Keeps working. Askr keeps watching.

The threshold for Trigger A is ~90% — before compaction fires.
The threshold for Trigger B is quota pace ahead of time remaining by a configurable margin.

---

# Session Resume Mechanism

Both triggers use the same resume mechanism: `handover.md`.

Written before every checkpoint. Read at every session start.

Contents:
- Current objective (one sentence)
- Exact next step (what to do immediately)
- Decisions made this session
- Files modified and why
- Test status
- Known blockers
- Context Claude needs to continue without any re-explaining

When Askr starts a new session, Claude reads `handover.md` first. No manual setup. No re-explaining. Work continues.

---

# Project State Files

```
askr/state/

handover.md              ← primary resume file, per developer
handover_<name>.md       ← co-founder's resume file
architecture.md          ← shared system design, last-write-wins
current_task.md          ← active objective, per developer
implementation_state.md  ← sections per developer, what's done/in-progress
decisions.md             ← append-only log, never conflicts
blockers.md              ← known issues, pending decisions
checkpoints/             ← historical recovery points
```

All committed to git. All pushed on every checkpoint. All pulled on every session start.

---

# Team Sync

Both developers install Askr on the same repo.

```
Dev A works → Askr checkpoints → state committed + pushed
↓
Dev B opens session → Askr pulls → Claude reads Dev A's handover.md
↓
Dev B continues Dev A's work immediately
↓
No Slack. No standup. No re-explaining.
```

Ground truth is in the repo. Always.

---

## Conflict-Resistant File Design

Designed for two developers working simultaneously:

| File | Design | Why |
|---|---|---|
| `handover.md` | Per developer | Never conflicts |
| `current_task.md` | Per developer | Never conflicts |
| `decisions.md` | Append-only, timestamped | Never conflicts |
| `implementation_state.md` | Sections per developer | Rarely conflicts |
| `architecture.md` | Shared, last-write-wins | Occasional merge, easy to resolve |

---

# Architecture

```text
┌─────────────────────────────────────┐
│          DEVELOPER (x2)             │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│           CLAUDE CODE CLI           │
└──────────────┬──────────────────────┘
               │
        Claude Hooks +
        JSONL Session Files
               │
               ▼
┌─────────────────────────────────────┐
│         SESSION MONITOR             │
├─────────────────────────────────────┤
│ Context fill %                      │
│   → StatusLine remaining_percentage │
│ Context burn rate                   │
│   → JSONL message.usage per turn    │
│ Quota burn rate                     │
│   → tokens vs. 5-hour window        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       DUAL FORECAST ENGINE          │
├─────────────────────────────────────┤
│ Context forecast                    │
│   → fill rate per turn              │
│   → compaction ETA (~90%)           │
│                                     │
│ Quota forecast                      │
│   → tokens/minute burn rate         │
│   → 5-hour window exhaustion ETA    │
│   → exact reset timestamp           │
│                                     │
│ Output: which trigger fires next    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│        SAFE PAUSE ENGINE            │
├─────────────────────────────────────┤
│ SAFE: idle, tests passing,          │
│       git clean, no active writes   │
│                                     │
│ UNSAFE: tests running, file write   │
│         active, migration/deploy    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       CHECKPOINT ENGINE             │
├─────────────────────────────────────┤
│ Writes handover.md                  │
│ Updates all state files             │
│ Git commit + push                   │
│ Triggers appropriate response:      │
│   Trigger A → new session now       │
│   Trigger B → wait for quota reset  │
└──────────────┬──────────────────────┘
               │
       ┌───────┴───────┐
       ▼               ▼
┌────────────┐  ┌─────────────────┐
│ NEW SESSION│  │  WAIT + RESUME  │
│ IMMEDIATELY│  │  after reset    │
└────────────┘  └─────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│       NOTIFICATION ENGINE           │
├─────────────────────────────────────┤
│ Discord webhooks                    │
│                                     │
│ Events:                             │
│   Checkpoint complete               │
│   Session resumed                   │
│   Feature complete                  │
│   Morning report                    │
└─────────────────────────────────────┘
```

---

# Data Sources (What Makes Forecasting Real)

## StatusLine payload (every turn)
```json
{ "context_window": { "remaining_percentage": 62 } }
```
Live context fill rate. Available on every turn.

## JSONL session files
Location: `~/.claude/projects/<project>/<session-id>.jsonl`

Per turn:
```json
{ "message": { "usage": { "input_tokens": 48200, "output_tokens": 1840 } } }
```
Exact token growth rate. Quota burn rate. Reset timestamp from first entry.

## PostToolUse hook
For agent subagent calls: `tool_response.usage` with full token breakdown.

---

# Claude Hooks

| Hook | Purpose |
|---|---|
| `SessionStart` | git pull, load handover.md + state files into context |
| `UserPromptSubmit` | update current_task.md with active objective |
| `PostToolUse` | update implementation_state.md, track quota burn |
| `Stop` | write handover.md, update state files, git commit + push |
| `PreCompact` | emergency fallback if forecast missed threshold |

---

# StatusLine

```
Normal:
  Askr ✓  ctx:62%  quota:78%

Approaching threshold:
  Askr ⚠  ctx:88%  quota:71%  compaction soon

Checkpointing:
  Askr ⚙ Checkpointing

Waiting for quota reset:
  Askr ⏳ Reset in 1h 42m

Resumed:
  Askr ↺ Resumed  saved:47min
```

---

# Morning Report

The moment that creates word of mouth.

Developer leaves Claude working. Goes to bed. Askr manages all session transitions overnight. Wakes up to:

```
Askr — Night Report

Sessions:     6
Duration:     4h 23m
Time saved:   ~2h 10m

Completed:
  Auth middleware rewrite
  JWT validation (47 tests passing)

In Progress:
  Refresh token rotation (60%)

Decisions made:
  Token storage moved to httpOnly cookies
  OAuth deferred to next sprint

Files changed: 14
Next:          Complete refresh token rotation
```

---

# The ask CLI (Fallback Layer)

During quota resets, `ask` fills the dead time:

```bash
ask "cto: what should we tackle for refresh token rotation?"
ask "debug: why would httpOnly cookies fail on mobile safari?"
ask "ceo: is this worth building or should we use Auth0?"
```

Grounded in the project snapshot. Costs ~$0.001/query.

No wasted time during resets.

---

# Reliability First

If reliability and autonomy conflict:

Choose reliability.

Always.

One false checkpoint — one interruption at the wrong time — and developers uninstall.

Zero misfires is the standard.

Trust is the product.

---

# Success Metric

Dev A works on auth until midnight.

Askr detects quota running low at 11:40pm.

Safe pause confirmed.

Checkpoint written. State committed. Session stopped.

Quota resets at 4am.

Askr resumes automatically.

Work continues on refresh token rotation.

Dev B opens Claude at 9am.

Pulls state. Claude reads Dev A's handover.

Dev B continues exactly where Dev A left off.

No Slack message. No standup. No context reconstruction.

That is success.
