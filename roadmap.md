# Askr Roadmap

Building in public. Updated as work progresses.

---

## Phase 0  - Complete ✅

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
| Clean pipeline (no hardcoded strings) | ✅ Done |
| Log moved to `~/.config/askr/usage.log` (global, not per-project) | ✅ Done |
| `askr` CLI stub (session orchestration placeholder) | ✅ Done |
| Phase 1 module stubs (session/, hooks/, state/, notifications/) | ✅ Done |

---

## Phase 1 - Core State Loop

**Goal:** Both developers' Claude sessions always start informed. State persists across sessions via git. No manual handoff needed.

**Conflict-resistant file design (built in from the start):**

| File | Design | Conflict risk |
|---|---|---|
| `handover_<dev>.md` | One file per developer | None |
| `current_task_<dev>.md` | One file per developer | None |
| `decisions.md` | Append-only, timestamped lines | None (git merges appends) |
| `implementation_state.md` | Fenced sections per developer | Minimal |
| `architecture.md` | Shared, last-write-wins | Occasional, easy to resolve |
| `blockers.md` | Shared, last-write-wins | Occasional, easy to resolve |

**Stage P1-1: State file templates + developer config**

| Task | Status |
|---|---|
| `askr/state/templates/` with all 6 template files | 🔲 Todo |
| `askr/state/config.py` - load developer name from `~/.config/askr/config.json` | 🔲 Todo |

**Stage P1-2: State writer + reader**

| Task | Status |
|---|---|
| `askr/state/writer.py` - write/append to all state files | 🔲 Todo |
| `askr/state/reader.py` - load + format state for Claude context injection | 🔲 Todo |

**Stage P1-3: Claude Code hooks**

| Task | Status |
|---|---|
| `SessionStart` hook - git pull, inject state into context | 🔲 Todo |
| `UserPromptSubmit` hook - update `current_task_<dev>.md` | 🔲 Todo |
| `PostToolUse` hook - update `implementation_state.md` developer section | 🔲 Todo |
| `Stop` hook - generate `handover_<dev>.md`, git commit + push | 🔲 Todo |
| `PreCompact` hook - emergency checkpoint fallback | 🔲 Todo |

**Stage P1-4: askr init command**

| Task | Status |
|---|---|
| `askr init` - prompt for developer name, save to config | 🔲 Todo |
| Create `askr/state/` directory from templates | 🔲 Todo |
| Write hook commands into `.claude/settings.json` | 🔲 Todo |
| Handle existing `.claude/settings.json` (merge, not overwrite) | 🔲 Todo |

**Done when:** Dev B opens a session and Claude correctly describes what Dev A built last night without any manual input.

---

## Phase 2  - Session Orchestration

**Goal:** Askr intercepts before Claude degrades or quota runs out. Both triggers working autonomously.

**Target:** 2 weeks after Phase 1

| Feature | Status |
|---|---|
| JSONL session file monitoring (token growth per turn) | 🔲 Todo |
| StatusLine integration (`remaining_percentage` from payload) | 🔲 Todo |
| StatusLine display: `ctx:62%  quota:78%` | 🔲 Todo |
| Quota burn rate calculation (tokens/min vs. 5-hour window) | 🔲 Todo |
| Forecast engine: context ETA + quota ETA | 🔲 Todo |
| Safe pause detection (idle, no active writes, git clean) | 🔲 Todo |
| **Trigger A:** ~90% context → checkpoint → new session immediately | 🔲 Todo |
| **Trigger B:** quota low → checkpoint → wait → auto-resume | 🔲 Todo |
| Exact reset timestamp from JSONL first-entry + 5h | 🔲 Todo |
| `PreCompact` hook as emergency fallback | 🔲 Todo |
| Real use: run overnight, verify unattended continuation | 🔲 Todo |

**Done when:** Claude Code session hits quota at midnight. Askr checkpoints. Resumes at reset. Developer wakes up to continued progress.

---

## Phase 3  - Morning Report + Notifications

**Goal:** The wow moment. The tweet screenshot. The thing that makes people want it.

**Target:** 1 week after Phase 2

| Feature | Status |
|---|---|
| Discord webhook configuration | 🔲 Todo |
| Checkpoint complete notification | 🔲 Todo |
| Session resumed notification | 🔲 Todo |
| Morning report generation (sessions, time saved, completed, decisions, next step) | 🔲 Todo |
| Time-saved analytics (per session, daily, weekly) | 🔲 Todo |
| Feature complete detection + notification | 🔲 Todo |
| StatusLine: `Askr ↺ Resumed  saved:47min` | 🔲 Todo |

**Done when:** First real overnight morning report screenshot taken and posted.

---

## Phase 4  - Public Launch

**Goal:** GitHub launch. Build-in-public presence. First external users.

**Target:** 1 week after Phase 3

| Feature | Status |
|---|---|
| README polished with GIF/screenshot of morning report | 🔲 Todo |
| GIF of StatusLine during session transition | 🔲 Todo |
| Clean install story (`askr init` from scratch in < 2 min) | 🔲 Todo |
| GitHub release with changelog | 🔲 Todo |
| Twitter/X launch thread | 🔲 Todo |
| First external user onboarded | 🔲 Todo |
| `brew tap` / `brew install askr` | 🔲 Todo |

**Done when:** 50 GitHub stars. One external developer using it on their own project.

---

## Phase 5  - Hardening (Post-Launch)

**Goal:** Zero misfires. Trust is the product.

| Feature | Status |
|---|---|
| False positive audit (checkpoint should never fire mid-write, mid-test) | 🔲 Todo |
| Manual override: `askr pause` / `askr resume` | 🔲 Todo |
| Per-project config (threshold percentages, Discord webhook, developer name) | 🔲 Todo |
| Linux support | 🔲 Todo |
| Windows/WSL support | 🔲 Todo |
| Test suite for hook scripts | 🔲 Todo |

---

## Decisions Log

**2026-06-02**
- Autonomous Mode is primary. Companion Mode (VS Code/Desktop) deferred until core is stable.
- Two triggers confirmed: Trigger A (context ~90%, immediate new session) and Trigger B (quota low, wait for reset).
- 50% context = StatusLine warning only. Not a stop trigger.
- handover.md is the primary resume mechanism. Claude reads it on session start.
- State files committed to git. Team sync is a core feature, not an add-on.
- `ask` CLI confirmed as the fallback Q&A layer during quota resets. Already shipped.
- Per-developer file naming to prevent merge conflicts during simultaneous work.
- decisions.md is append-only + timestamped  - conflict-free by design.
- Business model: irrelevant for now. Build in public, get stars, establish reputation.

---

## Not Building (Decided Against)

| Idea | Reason |
|---|---|
| Companion Mode (VS Code/Desktop) first | No stable session creation API. Autonomous Mode has all the value. |
| Model-agnostic intelligence layer | Becomes Cursor without the IDE. Loses focus. |
| Slack / email notifications | Ship one platform (Discord) perfectly first. |
| Checkpoint at 50% context | That's the quality signal, not the action threshold. Action at ~90%. |
| Autonomous overnight as the MVP | Core state loop must work first. Overnight is Phase 2. |
