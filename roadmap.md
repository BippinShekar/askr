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
| `blockers.md` | Manual-only notes; auto-detected blockers live in per-dev `handover_<dev>.json` (`blockers[]`), aggregated read-side | None on the automated path; manual edits rare, easy to resolve |
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

## Phase 3.6 - Autonomous Guard Correction ✅

**Goal:** When the guard catches an architectural mistake, don't just warn — block the write, explain why to Claude inline, let Claude self-correct, then report the full incident to Discord. Zero developer intervention required.

The problem with Phase 3.5: the guard warns but doesn't act. Claude proceeds with the bad approach anyway. The warning lands in Discord after the damage is done. This phase makes the guard a hard stop — Claude sees the block reason, rewrites its approach, and Discord gets a before/after incident report automatically.

| Feature | Status |
|---|---|
| `PreToolUse` returns block signal — guard returns `{"decision": "block", "reason": "..."}` to cancel the write and surface explanation directly to Claude | ✅ Done |
| Block message quality — explanation must be specific enough for Claude to self-correct (not just "architectural issue") | ✅ Done |
| Discord pre-block alert — "guard blocked write to X — reason: ..." sent before Claude retries | ✅ Done |
| Discord resolution alert — after Claude retries and write succeeds, send "resolved — what changed" diff summary | ✅ Done |
| Block audit trail — `guard_log.md` records blocked attempts + resolution outcome | ✅ Done |
| Escape hatch — if Claude retries the same blocked write 2x, unblock and escalate to Discord as unresolved | ✅ Done |

**Done when:** Guard catches a real architectural mistake, blocks the write, Claude self-corrects without developer input, Discord shows the full incident (blocked → corrected) automatically.

---

## Phase 3.7 - Rich Visual Reports ✅

**Goal:** Replace text-wall Discord messages with a single shareable image — session stats, cost savings, context timeline, goals completed. The screenshot that makes people want askr.

The problem with Phase 3 Discord output: it's walls of text. Nobody screenshots a wall of text. This phase generates a real PNG — dark card, session timeline, token/cost delta — and sends it as a Discord file attachment. Generated in Python, sent, deleted. No screenshotting, no browser, no dependencies beyond matplotlib.

The killer stat: "without askr this session would have cost $X and hit the context wall at Y tokens. With askr: $Z saved, 0 interruptions." Immediately legible to any developer paying for Claude.

| Feature | Status |
|---|---|
| Cost calculation — tokens used × model rate, projected cost without askr checkpointing | ✅ Done |
| Session timeline image — context % curve, trigger fire point, goal completions marked | ✅ Done |
| Summary card — time saved, tokens saved, cost delta, files changed, goals completed | ✅ Done |
| Discord file attachment — send PNG via multipart/form-data, delete temp file after | ✅ Done |
| Fires on checkpoint (context + quota triggers) and goal completion | ✅ Done |
| Morning report image — daily rollup of all sessions, total saved, goals shipped | ✅ Done |

**Done when:** A checkpoint fires, Discord receives a dark-card PNG with session stats and cost savings that's worth screenshotting and posting.

---

## Phase 3.8 - Permission Continuity ✅

**Goal:** Auto-launched sessions never prompt for tool permissions. Full autonomy means zero interruptions — not just "new session starts" but "new session runs without asking you anything."

The problem: Claude Code permissions granted as "allow once" die with the session. Every auto-launched session starts cold and re-prompts for the same tools. This breaks unattended overnight runs the moment the first Bash or Edit call needs approval.

| Feature | Status |
|---|---|
| `askr init` writes baseline tools to `allowedTools` (settings.json) AND `permissions.allow` (settings.local.json) — first session never prompts | ✅ Done |
| Stop hook reads tool usage from session JSONL, adds any newly-used tools to both `allowedTools` and `permissions.allow` so next session inherits them | ✅ Done |
| `askr launch` shows which tools are pre-approved and which would still prompt | ✅ Done |
| Auto-launched sessions (from goal add or context trigger) get `--allowedTools` flag populated from settings at launch time | ✅ Done |

**Done when:** askr starts a new session autonomously overnight, runs Bash, Edit, Write, and git push without a single permission prompt.

---

## Phase 3.9 - Behavioral Preference Persistence

**Goal:** You never write CLAUDE.md manually. Askr detects when you give an instruction that should apply to every future session, and persists it automatically — confirmed by you in Cursor, or auto-persisted with Discord notification when headless.

The problem: every tool that claims to "remember" preferences still requires manual config files. You have to know what to write, where to write it, and remember to update it. In practice, you repeat the same instructions every session. This phase makes askr close that loop automatically — it reads what you actually said, extracts the behavioral signal, and writes it to the right place.

**Two-mode delivery (by context):**

| Context | Behavior |
|---|---|
| Cursor open | `behavior_confirm` IDE popup — shows detected rules with Keep / Discard. User confirms before anything is written. |
| Headless / autonomous | Auto-writes to CLAUDE.md immediately. Discord sends "Detected and persisted: X. `askr prefs remove` to undo." |

**Features:**

| Feature | Status |
|---|---|
| Stop hook scans user messages from session JSONL for behavioral instructions | 🔲 Todo |
| Haiku call extracts structured rules — filters task-specific instructions vs. persistent preferences | 🔲 Todo |
| Diff against existing CLAUDE.md — never re-surface already-persisted rules | 🔲 Todo |
| LLM classifies global (`~/.claude/CLAUDE.md`) vs. project-specific rule scope | 🔲 Todo |
| `behavior_confirm` notification type in extension — Keep / Discard buttons | 🔲 Todo |
| Headless path: auto-write + Discord "Detected and persisted: X. `askr prefs remove` to undo." | 🔲 Todo |
| `askr prefs` CLI — list all persisted behavioral rules across global + project CLAUDE.md | 🔲 Todo |
| `askr prefs remove "rule"` — delete a specific rule from CLAUDE.md | 🔲 Todo |
| `askr prefs pending` — list rules detected but not yet confirmed (Cursor was closed mid-session) | 🔲 Todo |
| Conservative detection — only fire notification when confidence is high; silent if ambiguous | 🔲 Todo |

**Done when:** You tell Claude "always build in stages and commit each stage" once. Askr detects it, asks you to confirm, writes it to CLAUDE.md. Every subsequent session — including overnight autonomous ones — follows that rule without you repeating it.

---

## Phase 3.10 - Implementation Guard Hardening

**Goal:** The guard is built. The data pipeline that feeds it is now automated. This phase closes the loop — every session contributes to a shared memory of what works and what doesn't, so Claude's contradictory suggestions are caught before they land in the codebase.

**The problem this solves:** Claude re-suggests rejected approaches every session. It forgets settled decisions as context grows. Architecture.md was static and useless. The guard had nothing real to check against.

| Stage | Feature | Status |
|---|---|---|
| S1 | Auto-capture `decisions.md` from stop hook — keyword-detects settled decisions each turn, no extra LLM call | ✅ Done |
| S2 | Cumulative `failed_approaches.md` — checkpoint appends rejected approaches cross-session, deduped | ✅ Done |
| S3 | Wire `failed_approaches.md` into guard check + fix guard JSON token limit (was 300, now 500) | ✅ Done |
| S4 | CLAUDE.md guard directive — explicit instruction to check decisions + failures before any edit, respected every message | ✅ Done |
| S5 | Auto-regenerate `architecture.md` from import/dependency analysis at each checkpoint — no longer static | ✅ Done |
| S6 | Mid-session context refresh — PostToolUse injects top decisions every 10 tool uses, counteracts context burial | ✅ Done |

**Honest risks:**
- Decision keyword extraction will over-capture non-decisions and under-capture subtle ones. Quality improves over sessions as the file populates.
- Architecture regeneration via grep is shallow. It improves as the codebase stabilises.
- Mid-session refresh may be ignored by Claude. It's defensive, not authoritative.

**Done when:** Claude makes a contradictory suggestion, the guard catches it, blocks the write, and Claude self-corrects with the specific constraint from decisions.md cited in its correction.

---

## Phase 3.11 — JSON Handover Schema
*Target: pre-stress-test*

**Goal:** Replace the .md handover with a structured JSON file. Every field typed, queryable, and programmatically mergeable across sessions. Foundation for everything in 3.12–3.17.

**Problem it solves:** The .md handover is a blob. Reader.py dumps it raw into context. Downstream code can't query "which files were in play last session" without grepping markdown. JSON gives typed fields that smart injection and the guard can use directly.

**Fields introduced:** `task`, `discussion_summary`, `accomplishments[]`, `in_progress[{file, what, last_line}]`, `next_actions[]` (ordered, 3–5, not 1), `decisions[]`, `user_rejected_decisions[]`, `failed_approaches[]`, `files_in_play[]`, `relational_files[{file, relationship, why}]`, `uncommitted_files[]`, `blockers[]`, `completion_pct`, `session_metadata`.

**On `last_line` accuracy:** PostToolUse already receives the exact `file_path`, `old_string`, and `new_string` for every Edit tool call. After each edit, find `new_string` in the file — that's the exact line. No LLM inference needed. A session state file (`~/.config/askr/edit_cursor.json`) tracks `{file, line, what_was_being_done}` updated on every write tool use, and is included directly in the JSON handover at checkpoint. Ground truth, not approximation.

| Stage | Change | Status |
|---|---|---|
| S1 | `post_tool_use.py` — on Write/Edit, find new content in file, write `{file, line, ts}` to `edit_cursor.json` | ✅ Done |
| S2 | New handover LLM prompt outputs JSON, not markdown | ✅ Done |
| S3 | `checkpoint.py` — merge `edit_cursor.json` into `in_progress[]` before LLM call | ✅ Done |
| S4 | `writer.py` write_handover writes .json (keeps .md as human-readable derived copy) | ✅ Done |
| S5 | `reader.py` load_own_handover reads JSON, formats targeted context string | ✅ Done |
| S6 | Migration: if .json missing, fall back to .md — no existing projects break | ✅ Done |
| S7 | `next_actions` prompt changed from "one action only" to "ordered list of 3-5" | ✅ Done |

**Honest risks:**
- LLM must output valid JSON every time. Malformed JSON = no handover. Need robust fallback: mechanical JSON construction from transcript + edit_cursor.json if LLM fails.
- JSON is harder for users to hand-edit when they want to fix a bad handover. Mitigation: always write a .md copy as human-readable view.

---

## Phase 3.12 — Ground-Truth Direction Inference ✅
*Target: pre-stress-test*

**Goal:** Autonomous sessions know what to work on from deterministic signals — not from transcript speculation. The handover's `next_actions[]` is cross-checked against git state before an autonomous session acts on it. A HITL confirmation gate fires only when inference confidence is low, preserving autonomy while eliminating token burn on wrong work.

**Problem it solves:** The current handover `next_actions[]` are LLM-inferred from conversational momentum — speculative by design. An autonomous session may inherit a stale directive (work already committed), a misread directive (discussion, not decision), or no directive at all (goals empty, roadmap not consulted). Result: sessions burn tokens verifying completed work or stall with no direction.

**Why explicit task queues are the wrong answer:** They break the autonomy story — the core adoption differentiator. If the user has to plan every session, askr is a fancy hand-off template. The direction must be inferred, not requested.

**Signal priority stack (deterministic before speculative):**

| Priority | Signal | Source | Reliability |
|---|---|---|---|
| 1 | Uncommitted files at session start | `git status` | Ground truth — work was interrupted here |
| 2 | Active blockers | `blockers.md` non-empty | Ground truth — this is what's stuck |
| 3 | Git log momentum | Last 10 commits, which files/areas | High — reveals where the codebase is moving |
| 4 | next_actions cross-checked against git | Drop any action whose artifact is already committed | High after cross-check, low before |
| 5 | Session arc from handover history | Last 5 `handover_<dev>.json` states via git log | Medium — quality depends on handover accuracy |
| 6 | Roadmap first `🔲 Todo` stage | `roadmap.md` parsed for next open stage | Low-medium — only works if roadmap is maintained |

**Session arc — free from existing git history:**
`handover_bippin.json` is committed after every session. `git log --follow -p askr_state/handover_bippin.json` gives every session's distilled state in chronological order — no new infrastructure. Reading the last 5 gives a project arc: what has been worked on across sessions, what direction momentum points toward. The arc is only as good as handover quality — this is why foundational handover fixes (3.11 + stop hook fixes) must precede this phase.

**HITL gate — only when inference is uncertain:**
The confirmation notification fires only when the top signal is weak (no uncommitted files, no blockers, git log is ambiguous). When the top signal is strong (uncommitted files exist, or blockers.md is non-empty), the autonomous session proceeds without a gate. The goal is that the gate fires <20% of the time — it is a safety net, not a workflow step.

| Stage | Change | Status |
|---|---|---|
| S1 | `checkpoint.py` handover prompt: change `task` field instruction to past-tense outcome ("what was accomplished") — eliminates "Remove X" vs "[x] Removed X" contradiction | ✅ Done |
| S2 | `checkpoint.py` — cross-check `next_actions[]` against `git log` before writing: drop any action whose target file+message match a recent commit | ✅ Done |
| S3 | `lifecycle.py` — `_infer_direction()`: reads uncommitted files → blockers.md → git log momentum, returns `{direction, confidence, signal_source}` | ✅ Done |
| S4 | `lifecycle.py` — `_read_session_arc()`: reads last 5 handover states from git log, extracts task+files_in_play per session, synthesises arc in one Haiku call | ✅ Done |
| S5 | `stop.py` — when writing re-launch notification, call `_infer_direction()` and embed result in the autonomous session prompt instead of raw next_action text | ✅ Done |
| S6 | HITL gate: when `_infer_direction()` confidence < 0.7, write `direction_confirm` notification — "Based on [signal], I plan to work on X. Confirm or redirect." 5-min timeout, then proceed | ✅ Done |

**Honest risks:**
- Session arc quality compounds handover quality. If handovers are speculative, 5 stacked summaries are worse than 1. S4 should be built last, after S1–S3 demonstrate that handover quality is reliable enough to stack.
- Git log momentum can mislead on recently-pivoted projects. If the last 10 commits are all on feature A but the developer just decided to pivot to feature B, momentum points backward. Blockers.md and uncommitted files take priority for this reason.
- HITL gate timeout (5 min, then proceed) means a sleeping developer wakes up to find the session started on the inferred direction. Wrong inference + unattended execution = real damage. Mitigation: gate should only proceed autonomously when confidence ≥ 0.85, stall otherwise.

---

## Phase 3.13 — User-Rejection Tracking
*Target: pre-stress-test*
*Last audited against code: 2026-07-09*

**Goal:** Track decisions Claude proposed that the user rejected. Separate from failed_approaches (technical dead ends) and decisions (settled choices). Feeds the implementation guard so it can catch re-suggestion of vetoed approaches across sessions.

**Problem it solves — validated:** This is the documented #1 pain point with Claude Code. GitHub issue #37314 on the official repo: *"Claude repeatedly fails to apply its own memory/feedback — same mistakes recur across sessions."* Qodo's State of AI Code Quality 2025 report: frustration drops from 44% to 16% when context is persistently stored and reused. Developers accept less than 44% of AI code generations — rejections happen constantly and are immediately forgotten. The user should never have to re-correct Claude about the same thing twice. Ever.

**What this is NOT:** Failed approaches (technical dead ends Claude tried and they broke). This is specifically: Claude proposed an approach, the user said no for a reason (style, architecture, preference, prior decision), and that veto must persist cross-session.

**New artifact:** `rejected_decisions.json` — cumulative, cross-session, append-only. Each entry: `{what_was_proposed, user_signal, domain, context_file, date, confidence}`.

| Stage | Change | Status |
|---|---|---|
| S1 | Handover LLM prompt extracts suggestion/rejection pairs from transcript with confidence score | ✅ Done — `user_rejected_decisions[]` field in handover LLM prompt, written into `handover_<dev>.json`/`.md` (`checkpoint.py:286,331,720`) |
| S2 | `checkpoint.py` — `_write_rejections_from_handover()` appends above-threshold entries to `rejected_decisions.json` | 🔲 Todo — rejections only live inside the per-dev handover, no standalone cumulative cross-session file |
| S3 | `pre_tool_use.py` guard — query `rejected_decisions.json` by domain/file before allowing writes | 🔲 Todo — blocked on S2 |
| S4 | Mid-session: `post_tool_use.py` also scans last user message in real time for high-confidence rejection signals, writes immediately (not just at checkpoint) | 🔲 Todo |
| S5 | CLAUDE.md guard directive updated: check `rejected_decisions.json` before any edit | 🔲 Todo — blocked on S2 |

**Current gap:** rejections are captured (S1) but don't survive past one handover cycle — nothing persists them cross-session or checks them before an edit, so a vetoed approach can still resurface in a later session.

**Honest risks:**
- "No, that's wrong" about the user's own code is structurally identical to rejecting Claude's suggestion. Extraction must classify the target of rejection, not just the rejection signal. Confidence threshold of 0.8 before writing — under-capture is acceptable, false positives in the guard erode trust faster than missed captures.
- Real-time detection in S4 (post_tool_use) runs on every tool call — must be fast. Cap at simple pattern matching for real-time; full LLM extraction only at checkpoint.

---

## Phase 3.14 — Incremental Snapshot as Architecture Source
*Target: pre-stress-test*

**Goal:** The `.llm_snapshot/summary.json` becomes the live, always-current architecture record. After every session, changed files are re-scanned, the reverse dependency graph is updated, and `architecture.md` becomes a derived view generated on demand — not a maintained file.

**Problem it solves:** Current architecture.md is regenerated from import lines by Haiku — shallow, speculative, wrong for JS/CSS-heavy projects. The snapshot already has real file content and LLM-generated purpose. It goes stale after init because nothing updates it. Any change to the codebase must be immediately and accurately reflected in the snapshot — it is the guiding light of the implementation guard.

**Update strategy — post-session batch, not mid-checkpoint per-file:**
Snapshot update happens in the Stop hook after the session ends, when we have complete knowledge of all changes. `git diff --name-only HEAD~1..HEAD` gives the exact set of changed files. All changed files are sent to Haiku in a single batched call (one API request, all files as separate items in the prompt). No per-file individual calls. No latency added to the checkpoint itself.

**Reverse dependency index — non-negotiable:**
If file B changes and file A imports B, file A's snapshot entry is now stale. The reverse dependency index maps `{file → files_that_import_it}`. Built at init from AST/regex import analysis, updated incrementally. Every changed file's importers are added to the re-scan batch automatically. This is not optional — without it, the snapshot lies.

| Stage | Change | Status |
|---|---|---|
| S1 | `qa/snapshot.py` — build reverse dependency index at init (regex import scan for Python + TS/JS) | 🔲 Todo |
| S2 | `qa/snapshot.py` — `update_snapshot_batch(files[])`: send all files in one Haiku call, parse structured response | 🔲 Todo |
| S3 | `stop.py` — after checkpoint, call `update_snapshot_batch(changed_files + their_importers)` | 🔲 Todo |
| S4 | Deleted files: compare snapshot keys against `git ls-files`, remove entries for missing files | 🔲 Todo |
| S5 | Renamed files: `git diff --name-status` detects R entries — update snapshot key, preserve history | 🔲 Todo |
| S6 | `reader.py` — `load_architecture()` reads from snapshot entries, not architecture.md | 🔲 Todo |
| S7 | Reverse dependency index persisted to `.llm_snapshot/rdep.json`, updated on each batch run | 🔲 Todo |

**Honest risks:**
- Haiku's context window is 200k tokens. 20 files at ~100 lines each is ~15k tokens — well within one call. But a session that changes 80 files across a large codebase approaches the limit. Need a token count check before batching and split into ≤2 calls if needed.
- The reverse dependency index built from regex import analysis will miss dynamic requires, re-exports through barrel files, and runtime-resolved imports. These gaps are acceptable — the index doesn't need to be perfect, just not wrong about what it does cover.
- Snapshot is now the authority. A bug that corrupts snapshot entries will silently mislead context injection and the guard. Need a validation step: snapshot entries must have non-empty `purpose` field or they are discarded and re-scanned.

---

## Phase 3.15 — Smart Context Injection
*Target: pre-stress-test*

**Goal:** Session start injection is precise and complete — not a dump, not a surgical cut. Pulls the exact context the current session's work requires: the in-play files, their relational context (what they depend on and what depends on them), and the decisions/rejections that are semantically relevant to the upcoming work. Nothing more, nothing less.

**Problem it solves:** Current `build_context_injection()` dumps everything regardless of relevance. By session 4 of a long project this burns 6–8% of the context window before Claude does anything. But naive filtering by file path alone is equally wrong — a session touching `api/auth.ts` needs context about `middleware/jwt.ts` even if it's not explicitly in files_in_play.

**Relational context is first-class:** The JSON handover (Phase 3.11) stores not just `files_in_play[]` but `relational_files[{file, relationship, why}]` — files that are architecturally connected to the session's work. This is populated by the handover LLM from the transcript (it knows which other modules were discussed, imported, or affected) and from the reverse dependency index (3.14). Context injection uses both sets.

**Relevance, not just recency:** Decisions and rejections are filtered by semantic match to the current session's task and files — not just "last N entries." A TF-IDF or lightweight embedding match against the handover's `task` field selects the most relevant prior decisions, regardless of when they were made.

| Stage | Change | Status |
|---|---|---|
| S1 | `reader.py` — `build_context_injection()` rewritten around `files_in_play` + `relational_files` from handover JSON | 🔲 Todo |
| S2 | Snapshot entries pulled for `files_in_play` + `relational_files` (union, deduped) | 🔲 Todo |
| S3 | Decisions: TF-IDF match against handover `task` + `next_actions` — top 10 by relevance score, not recency | 🔲 Todo |
| S4 | Rejected decisions: filter by `domain` field matching in-play or relational file paths | 🔲 Todo |
| S5 | Failed approaches: semantic match to current task, last 3 sessions as recency floor | 🔲 Todo |
| S6 | Context budget enforced: injection capped at 15% of model context window (~30k tokens), truncated by priority if exceeded | 🔲 Todo |
| S7 | Fallback: if `files_in_play` empty and no relational context, revert to full-dump (current behaviour) | 🔲 Todo |

**Honest risks:**
- Dependent on Phase 3.11 (JSON handover with relational_files) and Phase 3.14 (snapshot + rdep index). Build those first — this phase doesn't function without them.
- TF-IDF relevance matching is lightweight but imprecise for short decision strings. Acceptable for v1 — upgrade to embedding-based retrieval in Phase 6 if needed.
- The 15% context cap in S6 is a hard ceiling. If a session genuinely requires more context than that to continue safely, the cap will silently drop relevant information. Mitigation: order by priority (rejections > decisions > architecture > failed approaches) so most critical context survives a truncation event.

---

## Phase 3.16 — Emergency Handover Fix ✅
*Target: pre-stress-test*
*Last audited against code: 2026-07-09*

**Goal:** PreCompact generates a real, LLM-quality handover — not boilerplate. All trigger types go through the same handover path. SIGTERM fires only after the handover is complete — no fixed timeout, dynamic wait.

**Problem it solves:** The current emergency path outputs: "Emergency checkpoint triggered. Check implementation_state.md." This is generated when context is highest and Claude is mid-work — exactly when a good handover matters most. A fixed 60s timeout is the wrong model: SIGTERM should be a consequence of completion, not a race condition.

**Dynamic timeout design:** The PreCompact hook starts the Haiku call, waits for it to return, writes the file (Python `with` block guarantees flush on close), then sends SIGTERM. The hook's registered timeout in Claude Code settings is set high (120s) as an absolute ceiling — but in practice SIGTERM fires the moment the handover is written, typically 15–30s. No sleep, no polling, no race.

| Stage | Change | Status |
|---|---|---|
| S1 | Remove `if trigger_type == "emergency"` branch in `create_checkpoint` | ✅ Done — confirmed removed, `checkpoint.py:820-827` |
| S2 | Mechanical handover written first from transcript + `edit_cursor.json` (instant, no LLM) — safety net | ✅ Done |
| S3 | Haiku call runs, LLM handover overwrites mechanical version on success | ✅ Done — PreCompact routes through the same LLM handover path as normal checkpoints |
| S4 | SIGTERM sent only after file write + close completes. No fixed sleep. | ✅ Done |
| S5 | Update `HOOK_TIMEOUTS["PreCompact"]` from 60 to 120 in `askr.py` — ceiling, not target | ✅ Done |

**Honest risk:**
- If the Haiku call hangs indefinitely (API outage, network timeout), the hook blocks until Claude Code's 120s ceiling kills it. The mechanical handover written in S2 survives this — it's on disk before the LLM call starts. The next session gets the mechanical version, which is sparse but not the current useless boilerplate.

---

## Phase 3.17 — Auto-Populate decisions.md ✅
*Target: pre-stress-test*
*Last audited against code: 2026-07-09*

**Goal:** decisions.md is never empty. Every checkpoint extracts settled decisions from the same LLM pass that generates the handover and writes them automatically.

**Problem it solves:** The guard directive in CLAUDE.md says "check decisions.md before editing." The file is empty. The guard is checking a ghost.

| Stage | Change | Status |
|---|---|---|
| S1 | Handover LLM prompt adds `decisions[]` field to JSON output | ✅ Done — `checkpoint.py:285` |
| S2 | `checkpoint.py` — `_write_decisions_from_handover()` appends new decisions to `decisions.md` with dedup | ✅ Done — `checkpoint.py:425`, dedup via `_tail_decisions_jsonl`; git log confirms `decisions.jsonl` is committed automatically by askr's own `askr: idle`/`askr: checkpoint` commits |

**Honest risks:** Low. The only risk is over-extraction — every observation becomes a "decision." Mitigate with a tight prompt definition: a decision is a choice between alternatives that rules something out, not a factual statement.

---

## Phase 4 - Team Scale
*Target: pre-launch*
*Last audited against code: 2026-07-09*

**Goal:** Multiple developers, shared state, concurrent sessions without conflicts.

**Note:** the team-scoped directory layout originally planned here (P4-0:
`askr_state/teams/<team>/members/<dev>/...`) was superseded. Decision log
(2026-06-14/15/16) shows the actual build went with a flatter layout —
`askr_state/handover_<dev>.*`, `askr_state/tasks/queue_<dev>.jsonl` — plus
git `merge=union` on every shared append-only file (`.gitattributes`). That
gives conflict-free concurrent pushes without the team/member nesting, and
is the right scope for a 2-person team. Revisit team-scoped directories only
if/when headcount makes flat `askr_state/` unnavigable (~10+ devs).

**Stage P4-0: Team directory structure** — **Deferred, not needed at current scale.**

| Feature | Status |
|---|---|
| New directory structure with team scoping | ⏸ Deferred — flat layout + union-merge covers 2-person scale |
| `askr init` updated to write into team-scoped paths | ⏸ Deferred |
| Reader/writer updated to resolve paths via team config | ⏸ Deferred |

**Stage P4-1: Task queue per developer** — ✅ **Built**, but shipped ahead of its required gate.

Implemented as `askr_state/tasks/queue_<dev>.jsonl`, drained at `session_start.py:281` and injected directly into session context (`session_start.py:331-335`). Verified in code, not just this doc.

| Feature | Status |
|---|---|
| `askr task queue <dev> "..."` — append task to another developer's queue (`askr.py:1268`) | ✅ Done |
| `session_start.py` — drain queue, inject tasks into session context before first prompt | ✅ Done |
| Drained tasks archived with completion timestamp (`_drain_task_queue`, `session_start.py:179`) | ✅ Done |
| `askr task list [<dev>]` — show pending queue for a developer (`askr.py:1286`) | ✅ Done |
| **Approval gate (Phase 5) in place before dangerous-permission sessions run queued tasks** | ✅ Done — `permission_gate.py` (`is_dangerous_session`) invoked at `session_start.py:403`, writes `task_approval_pending` notification. Built 2026-07-02; this row was stale (contradicted the Phase 5 section below). |
| Drain-then-truncate sequence is race-free under concurrent queue writes | ✅ Done — `_drain_task_queue` wrapped in `file_lock()` (`session_start.py:170-191`) |

**Stage P4-2: `askr team` CLI** — ✅ **Built** (`cmd_team()`, `askr.py:1305`). Shows all developer handovers, last-seen, next action, live context % in one view.

**Stage P4-3: Concurrency and role awareness** — not built, genuinely future work, low priority at 2-person scale.

| Feature | Status |
|---|---|
| Live team dashboard: who's working on what, current session context %, blockers | 🔲 Todo |
| Conflict detection: alert when two developers' files_in_play overlap | 🔲 Todo |
| Shared decision arbitration: when decisions conflict across developers, surface for resolution | 🔲 Todo |
| Role-based context injection: frontend dev doesn't get backend architecture context by default | 🔲 Todo |
| VS Code extension UI (not just status bar) — full panel showing session state, goals, handover | 🔲 Todo |

---

## Phase 5 - Hardening
*Target: 1–2 months post-launch*
*Last audited against code: 2026-07-09*

**Goal:** Zero misfires. Trust is the product. Works on any machine, any project type.

| Feature | Status |
|---|---|
| False positive audit (checkpoint never fires mid-write, mid-test) | 🔲 Todo |
| Manual override: `askr pause` / `askr resume` | 🔲 Todo |
| Per-project config file (thresholds, Discord webhook, context trigger %) | ✅ Done — `askr_state/config.json` (gitignored as of 2026-06-17; was briefly committed with a live webhook secret in history — rotate that webhook if not already done) |
| Linux support (replace launchd with systemd) | 🔲 Todo |
| Windows/WSL support | 🔲 Todo |
| Test suite for all hook scripts | 🔲 Todo — grown to 188 tests across 13 files (up from 15); guard/permission-gate paths now covered (`test_guard_runner.py`, `test_pre_tool_use_guard.py`, `test_permission_gate.py`, `test_task_approval_gate.py`) but hook entrypoints themselves (`session_start.py`, `stop.py`, `user_prompt_submit.py`) still lack dedicated test files |
| `askr doctor` — diagnose common setup issues (venv missing, hooks not firing, JSONL not found) | 🔲 Todo |

**Approval Gate for Queued Tasks** — ✅ **Core enforcement built 2026-07-02.** Stage P4-1 above shipped the dangerous half (queue + auto-inject) without it; that gap is now closed at the enforcement layer. IDE popup rendering is still open (see below).

When another developer queues a task into your session, that task runs with whatever permissions your session already has — including permissions granted by Phase 3.8. Those were granted by you for your own work; they do not constitute authorization for someone else's task. `--dangerously-skip-permissions` bypasses Claude Code's own prompts entirely, so the gate must be an askr-level check, not a Claude Code permission check.

Trigger (any one condition is sufficient):
- `--dangerously-skip-permissions` present in session launch args
- `Bash(*)` or unrestricted Bash in `allowedTools`
- Any `rm` / delete pattern in `permissions.allow`

**Scope note (2026-07-09 audit):** this gate covers *queued-task execution* under dangerous permissions — it does not gate *session launch itself*. Nothing currently stops a session from launching with `--dangerously-skip-permissions` in the first place; that remains an open gap, tracked below as a pre-launch item.

Behavior when triggered + queued tasks exist: surface confirmation before any queued task executes. IDE popup if Cursor is open; Discord notification if headless. Tasks are blocked, not silently dropped.

| Feature | Status |
|---|---|
| `askr/session/permission_gate.py` — detect dangerous permission state from launch args + settings | ✅ Done |
| Block queued task execution when dangerous permissions + unconfirmed queue (`session_start.py` peeks instead of drains) | ✅ Done |
| `askr task approve` / `askr task discard` — resolve held tasks; approve is one-shot, doesn't disable the gate permanently | ✅ Done |
| Headless path: Discord notification (`task_approval_pending`) with task list + approve/discard instructions | ✅ Done |
| Non-dangerous sessions: queued tasks auto-run without gate (by design) | ✅ Done — unchanged existing path |
| IDE popup listing queued tasks + current permission state | 🔲 Todo — confirmed 2026-07-09: `extension.js` `checkNotification()` has explicit cases for `context`, `goal_launch`, `goal_check`, `reload_extension`, `direction_proposal`, `direction_confirm`/`direction_needed`, with a generic fallback for everything else. `task_approval_pending` and `guard_warning` both fall through to that generic popup — neither gets a purpose-built UI. |
| Gate askr's own autonomous relaunch when the triggering session is dangerous (distinct from the queued-task gate above) | ✅ Done 2026-07-09 — `_launch_gate_check()` in `lifecycle.py`, wired into `_start_claude()` (quota-trigger, goal-autolaunch) and `_open_companion_session()` (context-trigger). Holds the relaunch, writes a `dangerous_autolaunch_pending` notification + Discord alert, requires `askr launch approve` (one-shot flag, mirrors the task queue's `askr task approve`). Note: this does not and cannot prevent a user from manually typing `claude --dangerously-skip-permissions` themselves — that's outside askr's process entirely. It gates what askr itself does next once that state is detected. |

---

## Phase 6 - Architecture Intelligence
*Target: 3–4 months post-launch*

**Goal:** Askr understands your codebase at function level, not just file level. Engineers spend hours drawing call graphs and understanding module relationships. Askr generates and maintains these automatically, and uses them to give Claude targeted, accurate architectural context instead of dumping file summaries.

**Why this matters for Claude Code users:** The #1 time sink for engineers using Claude Code on large projects is context overhead — re-explaining "how does auth flow into the middleware?" every session. If askr can answer that from a live call graph, Claude starts informed every time without you repeating it.

| Stage | Feature | Status |
|---|---|---|
| S1 | AST-based call graph for Python (function → function calls) using `ast` module | 🔲 Todo |
| S2 | TypeScript call graph using `@typescript-eslint/parser` — function and import relationships | 🔲 Todo |
| S3 | Call graph stored in snapshot alongside file-level entries | 🔲 Todo |
| S4 | Mermaid diagram generation from call graph — `askr graph` CLI command | 🔲 Todo |
| S5 | Context injection uses call graph: if session touches function X, inject callers and callees of X | 🔲 Todo |
| S6 | Logic flow diagrams for route handlers (HTTP request → middleware chain → handler → response) | 🔲 Todo |
| S7 | Incremental call graph updates at checkpoint (only re-parse changed files) | 🔲 Todo |

**Honest risks:**
- Call graph generation for real codebases (dynamic dispatch, decorators, higher-order functions) is hard to do accurately. Python's `ast` module gets the static cases. Dynamic calls are invisible.
- TypeScript's type system makes accurate call graph extraction non-trivial without running the full TS compiler. The parser-based approach will miss indirect calls through interfaces.
- Mermaid diagrams for large codebases are unreadable. Need aggressive filtering — show only the subgraph relevant to the session's files_in_play.
- This is 3–4 weeks of focused work done right. Don't start it until the core handover pipeline is solid and external users are active.

---

## Phase 7 - Public Launch
*Target: post-stress-test*

**Goal:** GitHub launch. Build-in-public presence. First external users.

| Feature | Status |
|---|---|
| Stress test passes end-to-end (overnight Tetris build) | 🔲 Todo |
| Demo video: Claude building complex project across 5 autonomous sessions | 🔲 Todo |
| README polished — GIF of session transition, morning report | 🔲 Todo |
| Clean install story (`install.sh` from scratch in < 3 min) | 🔲 Todo |
| GitHub release with changelog | 🔲 Todo |
| Twitter/X launch thread with demo video | 🔲 Todo |
| First external user onboarded | 🔲 Todo |
| `brew tap askr` | 🔲 Todo |

**Done when:** 50 GitHub stars. One external developer using it on their own project without help.

---

## Phase 7.1 — Pre-Launch Audit (2026-07-02, re-audited 2026-07-09)

**Context:** Repo is already public on GitHub. Original audit found a live secret leak and confirmed several roadmap-flagged gaps were open in code, not just doc. Re-audited 2026-07-09 against current code — most items have since shipped.

| Severity | Finding | Status |
|---|---|---|
| — | Discord webhook committed in plaintext at `50eba93` | Closed — webhook rotated 2026-07-02, old token is dead. Not a live risk; history scrub not needed. |
| P0 | `Formula/askr.rb` cannot install askr: placeholder sha256, tag `v1.0.0` doesn't exist, only copies root `*.py` (misses entire `askr/` package), never creates `bin/askr` | ✅ Fixed — real tag `v0.1.0`, real pinned sha256, installs full `askr/` package + `bin/askr` entry point |
| P1 | Zero gate anywhere in `askr/` on `--dangerously-skip-permissions` sessions | Split into two distinct gaps on re-audit: queued-task execution under dangerous permissions is now gated (`permission_gate.py`, Phase 5, done 2026-07-02); **session launch itself is still ungated** — see Phase 4 P4-1 note above. |
| P1 | `pre_tool_use.py` cross-repo boundary check only covers Write/Edit/MultiEdit — Bash tool calls can still cross repo boundaries undetected | ✅ Fixed — `find_cross_repo_bash_path()` + dedicated Bash branch, `pre_tool_use.py:208,274` |
| P1 | PreCompact emergency handover still hardcoded boilerplate, doesn't route through LLM handover path | ✅ Fixed — see Phase 3.16 above |
| P1 | `pre_tool_use.py`/`guard_runner.py` — zero test coverage on the guard | ✅ Fixed — `test_guard_runner.py`, `test_pre_tool_use_guard.py`, `test_permission_gate.py` |
| P1 | README.md describes Phase 3 (notifications) and Phase 3.5 (guard) as "Coming Next" | ✅ Fixed — README no longer claims this; documents the real remaining `guard_warning`/`task_approval_pending` IDE gap instead |
| Verified fixed | P4-1 `_drain_task_queue` race (read-archive-truncate with no lock) | Confirmed fixed — wrapped in `file_lock()` |
| Verified fixed | Handover generation could bleed sibling-repo work into this repo's `askr_state/` | Fixed in `checkpoint.py` — `project_path` now passed explicitly into the LLM prompt |

**Remaining open items post re-audit:** session-launch-time `--dangerously-skip-permissions` gate, IDE popup rendering for `task_approval_pending`/`guard_warning` (Phase 5), Phase 3.13 S2-S5 (persisted rejection tracking), Phase 3.14/3.15 (snapshot-as-architecture, smart context injection), Phase 3.9 (behavioral preference persistence), and an unproven real overnight unattended run (Phase 2).

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

**2026-06-13 - Handover + architecture redesign**
- JSON handover replaces .md — typed fields, programmatic querying, targeted injection. .md kept as human-readable derived copy.
- User-rejected decisions tracked separately from failed_approaches — different signal, different use in guard.
- .llm_snapshot becomes live architecture source. architecture.md becomes derived view.
- Context injection becomes targeted via files_in_play, not a full state dump.
- "One action only" in Next Action removed — replaced with ordered list of 3–5 actions.
- Function-level call graphs deferred to Phase 6 (post-launch). Too complex to build correctly before stress test.
- decisions.md auto-populated from handover LLM pass — no separate LLM call needed.

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
