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

## Phase 3.11 — JSON Handover Schema
*Target: pre-stress-test*

**Goal:** Replace the .md handover with a structured JSON file. Every field typed, queryable, and programmatically mergeable across sessions. Foundation for everything in 3.12–3.16.

**Problem it solves:** The .md handover is a blob. Reader.py dumps it raw into context. Downstream code can't query "which files were in play last session" without grepping markdown. JSON gives typed fields that smart injection and the guard can use directly.

**Fields introduced:** `task`, `discussion_summary`, `accomplishments[]`, `in_progress[{file, what, last_known_line}]`, `next_actions[]` (ordered, 3–5, not 1), `decisions[]`, `user_rejected_decisions[]`, `failed_approaches[]`, `files_in_play[]`, `uncommitted_files[]`, `blockers[]`, `completion_pct`, `session_metadata`.

| Stage | Change | Status |
|---|---|---|
| S1 | New handover LLM prompt outputs JSON, not markdown | 🔲 Todo |
| S2 | `writer.py` write_handover writes .json (keeps .md as human-readable derived copy) | 🔲 Todo |
| S3 | `reader.py` load_own_handover reads JSON, formats targeted context string | 🔲 Todo |
| S4 | Migration: if .json missing, fall back to .md — no existing projects break | 🔲 Todo |
| S5 | `next_actions` prompt changed from "one action only" to "ordered list of 3–5" | 🔲 Todo |

**Honest risks:**
- LLM must output valid JSON every time. Malformed JSON = no handover. Need robust fallback parser + mechanical JSON construction from transcript if LLM fails.
- `last_known_line` in in_progress entries will often be wrong. Haiku can't reliably infer line numbers from transcript text. Treat as best-effort, not authoritative.
- JSON is harder for users to hand-edit when they want to fix a bad handover. Mitigation: always write a .md copy as human-readable view.

---

## Phase 3.12 — User-Rejection Tracking
*Target: pre-stress-test*

**Goal:** Track decisions Claude proposed that the user rejected. Separate from failed_approaches (technical dead ends) and decisions (settled choices). Feeds the implementation guard so it can catch re-suggestion of vetoed approaches.

**Problem it solves:** Claude re-proposes the same approach it got shot down on two sessions ago. The guard can't catch it because there's no record of the user veto — only the current session's context holds that signal, and it's lost at session end.

**New artifact:** `rejected_decisions.json` — cumulative, cross-session. Each entry: `{what_was_proposed, user_signal, context_file, date, confidence}`.

| Stage | Change | Status |
|---|---|---|
| S1 | Handover LLM prompt extracts suggestion/rejection pairs from transcript | 🔲 Todo |
| S2 | `checkpoint.py` writes extracted rejections to `rejected_decisions.json` | 🔲 Todo |
| S3 | `pre_tool_use.py` guard check queries `rejected_decisions.json` for the target file's domain | 🔲 Todo |
| S4 | CLAUDE.md guard directive updated to include rejected_decisions check | 🔲 Todo |

**Honest risks:**
- "No, that's wrong" about the user's own code looks identical to "no, don't do that" to Claude's suggestion. LLM extraction will conflate them. Needs confidence threshold — only write to file above 0.8 confidence.
- False positives in the guard are worse than false negatives. A spurious rejection block erodes trust fast. Better to under-capture than over-capture.

---

## Phase 3.13 — Incremental Snapshot as Architecture Source
*Target: pre-stress-test*

**Goal:** The `.llm_snapshot/summary.json` becomes the live, always-current architecture record. At each checkpoint, only changed files are re-scanned and their entries updated. `architecture.md` becomes a derived view, not a maintained file.

**Problem it solves:** Current architecture.md is regenerated from import lines by Haiku — shallow, speculative, wrong for JS/CSS-heavy projects. The snapshot already has real file content and LLM-generated purpose. It just goes stale after init.

| Stage | Change | Status |
|---|---|---|
| S1 | `qa/snapshot.py` — add `update_snapshot_for_files(changed_files[])` function | 🔲 Todo |
| S2 | `checkpoint.py` — replace `_regenerate_architecture_md` with `_update_snapshot_for_changed_files` using `git diff --name-only HEAD` | 🔲 Todo |
| S3 | `reader.py` — `load_architecture()` reads from snapshot entries, not architecture.md | 🔲 Todo |
| S4 | Build reverse dependency index: if file B changes and file A imports B, re-scan A too | 🔲 Todo |
| S5 | Handle deleted/renamed files: remove stale snapshot entries on checkpoint | 🔲 Todo |

**Honest risks:**
- LLM calls per changed file at checkpoint adds latency proportional to session breadth. A session touching 20 files = 20 Haiku calls. Need batching (send files in groups of 5) or a threshold above which a full re-snapshot runs instead.
- Reverse dependency index in S4 is non-trivial. Without it, consumers of changed files have stale entries. Initial implementation can skip it and accept this limitation.
- Snapshot was designed for read-only Q&A. Making it the authority for context injection raises the cost of any snapshot bug.

---

## Phase 3.14 — Smart Context Injection
*Target: pre-stress-test*

**Goal:** Session start injection is targeted. Use `files_in_play` from the JSON handover to pull only relevant snapshot entries, filtered decisions, and recent (not cumulative) failed approaches. Stops the context dump from eating 8,000+ tokens before Claude does anything.

**Problem it solves:** Current `build_context_injection()` dumps everything: full handover, all team handovers, all current tasks, last 20 decisions, full architecture, all blockers. By session 4 of a long project this consumes 6–8% of the context window before work starts.

| Stage | Change | Status |
|---|---|---|
| S1 | `reader.py` — `build_context_injection()` rewritten: pull snapshot entries only for `files_in_play` | 🔲 Todo |
| S2 | Decisions filtered to those referencing in-play files or their module path | 🔲 Todo |
| S3 | Failed approaches: last 3 sessions only, not full cumulative log | 🔲 Todo |
| S4 | Rejected decisions: filter to domain of files_in_play | 🔲 Todo |
| S5 | Fallback: if files_in_play empty, revert to current full-dump behaviour | 🔲 Todo |

**Honest risks:**
- Dependent on Phase 3.11 (JSON with files_in_play) and Phase 3.13 (snapshot as architecture). If either is incomplete, this phase doesn't work.
- Relevance filtering by file path is blunt. A session touching `api/auth.ts` also needs context about `middleware/jwt.ts`. Without the reverse dependency index from 3.13, this cross-file relevance is missed.
- Under-injection is as dangerous as over-injection. If the session starts with too little context, Claude goes in the wrong direction silently. The fallback in S5 is the safety net.

---

## Phase 3.15 — Emergency Handover Fix
*Target: pre-stress-test*

**Goal:** PreCompact generates a real, LLM-quality handover — not boilerplate. All trigger types go through the same handover path.

**Problem it solves:** The current emergency path outputs: "Emergency checkpoint triggered. Check implementation_state.md." This is generated when context is highest and Claude is mid-work — exactly when a good handover matters most.

| Stage | Change | Status |
|---|---|---|
| S1 | Remove `if trigger_type == "emergency"` branch in `create_checkpoint` | 🔲 Todo |
| S2 | Write mechanical handover from transcript first (safety net, no LLM) | 🔲 Todo |
| S3 | Then call LLM to improve it and overwrite — LLM result replaces mechanical version | 🔲 Todo |
| S4 | Sequence: mechanical write → LLM call → overwrite → SIGTERM. SIGTERM only after both writes. | 🔲 Todo |

**Honest risks:**
- PreCompact timeout is 60s. LLM call takes 8–25s. SIGTERM must fire after the handover is written. If LLM hangs, the mechanical version is the fallback — this is acceptable.
- The race condition between handover write and process kill requires explicit sequencing. Get this wrong and you SIGTERM before the file is flushed.

---

## Phase 3.16 — Auto-Populate decisions.md
*Target: pre-stress-test*

**Goal:** decisions.md is never empty. Every checkpoint extracts settled decisions from the same LLM pass that generates the handover and writes them automatically.

**Problem it solves:** The guard directive in CLAUDE.md says "check decisions.md before editing." The file is empty. The guard is checking a ghost.

| Stage | Change | Status |
|---|---|---|
| S1 | Handover LLM prompt adds `decisions[]` field to JSON output | 🔲 Todo |
| S2 | `checkpoint.py` — `_write_decisions_from_handover()` appends new decisions to `decisions.md` with dedup | 🔲 Todo |

**Honest risks:** Low. The only risk is over-extraction — every observation becomes a "decision." Mitigate with a tight prompt definition: a decision is a choice between alternatives that rules something out, not a factual statement.

---

## Phase 4 - Public Launch
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

## Phase 5 - Hardening
*Target: 1–2 months post-launch*

**Goal:** Zero misfires. Trust is the product. Works on any machine, any project type.

| Feature | Status |
|---|---|
| False positive audit (checkpoint never fires mid-write, mid-test) | 🔲 Todo |
| Manual override: `askr pause` / `askr resume` | 🔲 Todo |
| Per-project config file (thresholds, Discord webhook, context trigger %) | 🔲 Todo |
| Linux support (replace launchd with systemd) | 🔲 Todo |
| Windows/WSL support | 🔲 Todo |
| Test suite for all hook scripts | 🔲 Todo |
| `askr doctor` — diagnose common setup issues (venv missing, hooks not firing, JSONL not found) | 🔲 Todo |
| Phase 3.9: Behavioral preference persistence | 🔲 Todo |

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

## Phase 7 - Team Scale
*Target: 5–6 months post-launch*

**Goal:** Multiple developers, shared state, concurrent sessions without conflicts. The state model was designed for teams — this phase makes it actually work under concurrent load.

| Feature | Status |
|---|---|
| Live team dashboard: who's working on what, current session context %, blockers | 🔲 Todo |
| Conflict detection: alert when two developers' files_in_play overlap | 🔲 Todo |
| Shared decision arbitration: when decisions conflict across developers, surface for resolution | 🔲 Todo |
| Role-based context injection: frontend dev doesn't get backend architecture context by default | 🔲 Todo |
| `askr team` CLI — show all developer handovers, sessions, goals in one view | 🔲 Todo |
| VS Code extension UI (not just status bar) — full panel showing session state, goals, handover | 🔲 Todo |

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
