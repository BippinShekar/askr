# Askr Roadmap

Building in public. Updated as work progresses.

---

## Phase 0 - Complete ✅

**The ask CLI + package restructure**

A fast, low-token, codebase-aware Q&A tool. The fallback layer during Claude Code quota resets.
Restructured into a proper Python package ready for Phase 1 expansion.

| Feature | Status |
|---|---|
| `ask` CLI entry point | ✅ Done |
| Incremental codebase snapshot | ✅ Done |
| Multi-mode responses (cto/ceo/debug/sales/deep/quick/web) | ✅ Done |
| Claude Haiku + OpenAI fallback | ✅ Done |
| Usage + cost tracking | ✅ Done |
| Git diff integration (debug mode) | ✅ Done |
| Auto-copy to clipboard | ✅ Done |
| `.askr_history` per project | ✅ Done |
| Global install via `install.sh` | ✅ Done |
| Package structure (`askr/`) | ✅ Done |
| Concurrent snapshot (6x faster, ThreadPoolExecutor) | ✅ Done |
| Multi-language dependency graph (TS/JS/Go/Ruby/Rust/Swift) | ✅ Done |
| Clean pipeline, no hardcoded strings | ✅ Done |
| Log moved to `~/.config/askr/usage.log` | ✅ Done |
| `askr` CLI entry point | ✅ Done |
| Phase 1 module stubs (session/, hooks/, state/, notifications/) | ✅ Done |

---

## Phase 1 - Complete ✅

**Goal:** Both developers' Claude sessions always start informed. State persists across sessions via git. No manual handoff needed.

**Conflict-resistant file design:**

| File | Design | Conflict risk |
|---|---|---|
| `handover_<dev>.md` | One file per developer | None |
| `current_task_<dev>.md` | One file per developer | None |
| `decisions.md` | Append-only, timestamped lines | None |
| `implementation_state.md` | Fenced sections per developer | Minimal |
| `architecture.md` | Shared, last-write-wins | Occasional, easy to resolve |
| `blockers.md` | Shared, last-write-wins | Occasional, easy to resolve |
| `goals.md` | Shared, Done section append-only | Minimal |

**Stage P1-1: State file templates + developer config** ✅

| Task | Status |
|---|---|
| `askr/state/templates/` with all 7 template files (incl. goals) | ✅ Done |
| `askr/state/config.py` - developer name + absolute project path | ✅ Done |
| Absolute project path stored in config - hooks work regardless of CWD | ✅ Done |

**Stage P1-2: State writer + reader** ✅

| Task | Status |
|---|---|
| `askr/state/writer.py` - write/append to all state files | ✅ Done |
| `askr/state/reader.py` - load + format state for Claude context injection | ✅ Done |
| `askr/state/goals.py` - add, complete, load, format goals for context | ✅ Done |

**Stage P1-3: Claude Code hooks** ✅

| Task | Status |
|---|---|
| `SessionStart` - git pull, inject state + today's goals into context | ✅ Done |
| `UserPromptSubmit` - strip IDE metadata tags, append to current_task (last 5) | ✅ Done |
| `PostToolUse` - update implementation_state.md developer section | ✅ Done |
| `Stop` - generate handover, infer goal completion, commit + push | ✅ Done |
| `PreCompact` - emergency checkpoint fallback | ✅ Done |
| `Notification` - HITL stub (Discord wired in Phase 3) | ✅ Done |

**Stage P1-4: askr init command** ✅

| Task | Status |
|---|---|
| `askr init` - developer name, save absolute project path | ✅ Done |
| `askr init` - generates real `architecture.md` from codebase snapshot | ✅ Done |
| `askr init` - generates real `implementation_state.md` from snapshot | ✅ Done |
| `askr init` - falls back to templates if no snapshot (prompts: run `ask init` first) | ✅ Done |
| Hook commands written into `.claude/settings.json` (merge, not overwrite) | ✅ Done |
| `askr status` - show state, snapshot, hooks, handover presence | ✅ Done |
| `askr_state/` at project root, separate from Python package code | ✅ Done |

**Stage P1-5: Goals tracking** ✅

| Task | Status |
|---|---|
| `askr_state/goals.md` - shared, product-level, date-organized | ✅ Done |
| `askr goal add "..."` - adds to today | ✅ Done |
| `askr goal add "..." --backlog` - adds to backlog | ✅ Done |
| `askr goal done "..."` - marks complete with timestamp | ✅ Done |
| `askr goals` - list today, backlog, done today | ✅ Done |
| `askr init` creates `goals.md` from template | ✅ Done |
| `SessionStart` injects today's goals into Claude context | ✅ Done |
| `Stop` infers goal completion from session transcript via LLM | ✅ Done |
| `SessionStart` auto-suggests goals from handover when none set | ✅ Done |

**Done when:** Dev B opens a session, Claude knows today's goals and last handover without being told. Session ends, completed goals marked done, state committed and pushed automatically.

---

## Phase 2 - Session Orchestration ✅

**Goal:** Askr intercepts before Claude degrades or quota runs out. Both triggers working autonomously. Goals drive what Claude works on.

| Feature | Status |
|---|---|
| JSONL session file monitoring (token growth per turn) | ✅ Done |
| StatusLine display: `ctx:X% quota:Y%` with ETA suffix | ✅ Done |
| Quota burn rate calculation (output tokens vs. 5-hour window) | ✅ Done |
| Dual forecast engine: context ETA + quota ETA, whichever fires first | ✅ Done |
| Safe pause detection (git clean, no test runners, no active writes) | ✅ Done |
| Trigger A: ~90% context → checkpoint → new session immediately | ✅ Done |
| Trigger B: quota low → checkpoint → wait for reset → auto-resume | ✅ Done |
| Exact reset timestamp from JSONL first-entry + 5h | ✅ Done |
| `askr launch` - daemon status, restart, stop | ✅ Done |
| Session marks goal done on completion, picks next goal | ✅ Done |
| launchd service — daemon starts at login, always-on, no manual step | ✅ Done |
| `caffeinate -i` — auto when session active, releases when idle | ✅ Done |
| Battery warning at init + daemon startup | ✅ Done |
| Real use: run overnight, verify unattended continuation + goal tracking | 🔲 Verify |

**Done when:** Claude Code session hits quota at midnight. Askr checkpoints. Resumes at reset. Developer wakes up to continued progress with goals updated.

---

## Phase 3 - Notifications + Morning Report + Team Brief ✅

**Goal:** The wow moment. The tweet screenshot. The thing that makes people want it. And the thing that makes a team not need Slack for status.

| Feature | Status |
|---|---|
| Discord webhook configuration (`ASKR_DISCORD_WEBHOOK` in `.env`) | ✅ Done |
| Checkpoint complete notification (context/quota/manual/emergency) | ✅ Done |
| Session resumed notification | ✅ Done |
| Morning report — `askr report` command, sessions + time saved + goals + next action | ✅ Done |
| Time-saved analytics (per session, daily total, shown in `askr status`) | ✅ Done |
| Goal completed notification (fires when stop hook marks a goal done) | ✅ Done |
| HITL notification — Notification hook forwards to Discord overnight | ✅ Done |
| End-of-session team broadcast — goals completed + files changed, replaces standup | ✅ Done |
| StatusLine: `Askr ↺ Resumed saved:Xm` after a context/quota cycle | ✅ Done |
| `askr_state/project_brief.md` — human-readable team brief, regenerated at every checkpoint | ✅ Done |
| Discord client — `askr/clients/discord.py` with Cloudflare-compatible User-Agent | ✅ Done |
| Stop/PreCompact hook timeout raised to 60s — Haiku API call needs headroom | ✅ Done |

**Note:** Daily goal summary is covered by the end-of-session broadcast + `askr report`. Not a separate feature.

**project_brief.md** is generated by Haiku at each checkpoint from the cumulative decisions log, architecture snapshot, completed goals, and handover history. Written for a person, not Claude — answers "what is this product right now, what's in flight, what's been decided, what should I pick up." A co-founder or new hire does `git pull`, reads one file, and is unblocked. No standup, no Slack ping needed.

**Done when:** First real overnight morning report screenshot taken and posted to Twitter/X. Co-founder pulls and is fully oriented from `project_brief.md` alone.

---

## Phase 3.5 - Implementation Guard ✅

**Goal:** Catch architectural holes and bad implementation approaches before Claude writes a single line — not after an hour of debugging to revert.

The problem: Claude sounds confident even when the approach has structural gaps. By the time you realise it's wrong, you've already got half a feature implemented the wrong way. This phase puts a lightweight reviewer between Claude's plan and Claude's first edit.

| Feature | Status |
|---|---|
| `PreToolUse` hook — detects significant operations (new file, batch edits ≥3, shared interface edit) | ✅ Done |
| Haiku cross-check — plan vs. `architecture.md` + `handover.md` + `decisions.md` for contradictions | ✅ Done |
| Flags: missing dependencies, API surface mismatches, assumptions conflicting with real codebase | ✅ Done |
| Async delivery — guard runner spawned as detached subprocess, Claude's tool not blocked | ✅ Done |
| Warning surfaced via IDE popup (`notification.json` → `guard_warning` type) + Discord | ✅ Done |
| Non-blocking — user sees warning, Claude proceeds, user decides whether to intervene | ✅ Done |
| 5-minute cooldown — guard doesn't re-trigger on every write in the same batch | ✅ Done |
| `askr_state/guard_log.md` — append-only audit trail of warnings raised | ✅ Done |

**Done when:** Claude proposes a plan with a real architectural hole, askr surfaces a warning before the first file is touched, developer avoids a 30-minute revert.

---

## Phase 3.6 - Autonomous Guard Correction

**Goal:** When the guard catches an architectural mistake, don't just warn — block the write, explain why to Claude inline, let Claude self-correct, then report the full incident to Discord. Zero developer intervention required.

The problem with Phase 3.5: the guard warns but doesn't act. Claude proceeds with the bad approach anyway. The warning lands in Discord after the damage is done. This phase makes the guard a hard stop — Claude sees the block reason, rewrites its approach, and Discord gets a before/after incident report automatically.

| Feature | Status |
|---|---|
| `PreToolUse` returns block signal — guard returns `{"decision": "block", "reason": "..."}` to cancel the write and surface explanation directly to Claude | ✅ Done |
| Block message quality — explanation must be specific enough for Claude to self-correct (not just "architectural issue") | ✅ Done |
| Discord pre-block alert — "guard blocked write to X — reason: ..." sent before Claude retries | ✅ Done |
| Discord resolution alert — after Claude retries and write succeeds, send "resolved — what changed" diff summary | 🔲 Todo |
| Block audit trail — `guard_log.md` records blocked attempts + resolution outcome | ✅ Done |
| Escape hatch — if Claude retries the same blocked write 2x, unblock and escalate to Discord as unresolved | ✅ Done |

**Done when:** Guard catches a real architectural mistake, blocks the write, Claude self-corrects without developer input, Discord shows the full incident (blocked → corrected) automatically.

---

## Phase 4 - Public Launch

**Goal:** GitHub launch. Build-in-public presence. First external users.

| Feature | Status |
|---|---|
| README polished with GIF/screenshot of morning report | 🔲 Todo |
| GIF of StatusLine during session transition | 🔲 Todo |
| Clean install story (`ask init` + `askr init` from scratch in < 3 min) | 🔲 Todo |
| GitHub release with changelog | 🔲 Todo |
| Twitter/X launch thread | 🔲 Todo |
| First external user onboarded | 🔲 Todo |
| `brew tap` / `brew install askr` | 🔲 Todo |

**Done when:** 50 GitHub stars. One external developer using it on their own project.

---

## Phase 5 - Hardening

**Goal:** Zero misfires. Trust is the product.

| Feature | Status |
|---|---|
| False positive audit (checkpoint never fires mid-write, mid-test) | 🔲 Todo |
| Manual override: `askr pause` / `askr resume` | 🔲 Todo |
| Per-project config (thresholds, Discord webhook) | 🔲 Todo |
| Linux support | 🔲 Todo |
| Windows/WSL support | 🔲 Todo |
| Test suite for hook scripts | 🔲 Todo |

---

## Decisions Log

**2026-06-02 - Planning session**
- Autonomous Mode primary. Companion Mode (VS Code/Desktop) deferred - no stable session creation API.
- Two triggers: Trigger A (context ~90%, immediate new session) and Trigger B (quota low, wait for reset).
- 50% context = StatusLine warning only, not a stop trigger.
- handover.md is the primary session resume mechanism.
- State files committed to git. Team sync is core, not add-on.
- `ask` CLI is the fallback Q&A layer during quota resets.
- Per-developer file naming prevents merge conflicts.
- decisions.md is append-only + timestamped - conflict-free by design.
- Business model irrelevant for now. Build in public, get stars, establish reputation.

**2026-06-02 - Phase 1 build decisions**
- `askr_state/` moved to project root, separate from Python package (`askr/state/` is code only).
- `.claude/settings.json` excluded from git - contains machine-specific absolute paths. Each developer runs `askr init` once.
- Absolute project path stored in `~/.config/askr/config.json` during init - hooks use it so CWD never matters.
- `askr init` runs a Claude Haiku call over the codebase snapshot to generate real `architecture.md`. Falls back to template if no snapshot.
- `implementation_state.md` pre-populated from snapshot's top-ranked files on init.
- `current_task_<dev>.md` changed from single-overwrite to append with last 5 entries + timestamps.
- IDE metadata tags (`<ide_opened_file>`, `<ide_selection>`, etc.) stripped from prompts before writing current_task.
- Goals feature added to Phase 1 (state + tracking), Phase 2 (autonomous execution), Phase 3 (Discord notifications).
- `Notification` hook added for HITL forwarding - stub in Phase 1, Discord wired in Phase 3.
- `.askr_history` removed from .gitignore - Q&A log is useful traceability for both developers.

---

## Not Building (Decided Against)

| Idea | Reason |
|---|---|
| Companion Mode first | No stable session creation API. Autonomous Mode has all the value. |
| Model-agnostic intelligence layer | Becomes Cursor without the IDE. No structural advantage. |
| Slack / email notifications | Ship one platform (Discord) perfectly first. |
| Checkpoint at 50% context | Quality signal only, not action threshold. Action at ~90%. |
| Autonomous overnight as MVP | Core state loop had to work first. Overnight is Phase 2. |
