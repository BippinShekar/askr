# askr

**Autonomous session orchestration for Claude Code. Built for co-founders who use Claude Code to build.**

Two problems. One tool.

1. **Session exhaustion** — Claude hits context or quota limits mid-task. Work stops. Recovery is manual and painful.
2. **Team drift** — your co-founder doesn't know what you built last night. You explain it again. On Slack. Like animals.

Askr fixes both. It monitors your sessions, checkpoints before Claude degrades, resumes automatically, and keeps your project state in git so both developers are always in sync — no Slack, no standups, no re-explaining.

> Claude may stop. Work must not.

---

## How It Works

Askr runs two things in parallel:

**Session Orchestration** — hooks into Claude Code's lifecycle. Monitors context fill and quota burn rate simultaneously. Intercepts before Claude's lossy auto-compaction fires. Writes a complete `handover.md`. Starts a fresh session immediately (context reset) or waits for quota reset and resumes automatically.

**Project State** — maintains a set of structured markdown files (architecture, decisions, current task, implementation state) that get committed to git on every checkpoint. Both developers pull this state at session start. Claude reads it automatically. Your co-founder's Claude knows what you built last night.

---

## Two Triggers

**Trigger A: Context near compaction (~90%)**
```
Context approaching limit
→ Askr intercepts before lossy auto-compact
→ Writes handover.md
→ Stops session
→ Starts new session immediately (no waiting)
→ Claude continues from exact next step
```

**Trigger B: Quota running low**
```
5-hour window nearly exhausted
→ Askr checkpoints + commits
→ Stops session
→ Waits for quota reset (exact time known from JSONL)
→ Auto-resumes after reset
→ Claude continues from exact next step
```

The 50% context mark is a StatusLine warning only. No interruption.

---

## The ask CLI (Already Shipped)

During quota resets, the `ask` CLI fills dead time with grounded answers:

```bash
ask "cto: best way to structure the auth layer?"
ask "debug: getting a 401 on every login attempt"
ask "ceo: should we build this or use Auth0?"
```

Fast, low-token (~$0.001/query), grounded in your actual codebase snapshot. Works from any project directory.

---

## Current State

The `ask` CLI is shipped and working. Session orchestration is in active development.

**Working now:**
- `ask` — codebase Q&A via Claude Haiku or OpenAI
- Incremental codebase snapshots
- Multi-mode responses (cto / ceo / debug / sales / deep / quick / web)
- Usage + cost tracking
- Git diff integration for debug mode

**Building now:**
- Claude Code hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop)
- State files (handover.md, decisions.md, architecture.md, current_task.md)
- Dual-limit monitoring (context% + quota burn rate)
- Predictive checkpointing (Trigger A + Trigger B)
- Autonomous session recreation
- Team sync via git

**Coming next:**
- StatusLine (live context% + quota%)
- Morning report to Discord
- Time-saved analytics
- `brew install askr`

---

## Install (ask CLI)

```bash
git clone https://github.com/BippinShekar/askr.git
cd askr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add your API keys to .env
bash install.sh
source ~/.zshrc
```

Now `ask` works from any directory.

---

## Using the ask CLI

```bash
cd ~/your-project
ask init             # index your codebase (run once)

ask "cto: ..."       # architectural decision
ask "ceo: ..."       # product/business decision
ask "debug: ..."     # bug fix (includes recent git diff)
ask "deep: ..."      # thorough explanation
ask "quick: ..."     # one-liner answer
ask "web: ..."       # live web search

ask snap             # force snapshot rebuild
ask log              # show usage + cost this week
```

Responses are auto-copied to clipboard. Every Q&A saved to `.askr_history`.

---

## StatusLine (Coming Soon)

```
Askr ✓  ctx:62%  quota:78%          ← normal
Askr ⚠  ctx:88%  quota:71%          ← approaching
Askr ⚙ Checkpointing                ← active
Askr ⏳ Reset in 1h 42m             ← waiting
Askr ↺ Resumed  saved:47min         ← restored
```

---

## Morning Report (Coming Soon)

```
Askr — Night Report

Sessions:    6
Duration:    4h 23m
Time saved:  ~2h 10m

Completed:
  Auth middleware rewrite
  JWT validation (47 tests passing)

In Progress:
  Refresh token rotation (60%)

Decisions:
  Token storage → httpOnly cookies
  OAuth deferred to next sprint

Next: Complete refresh token rotation
```

---

## Project Structure

```
askr/
├── ask.py              # CLI entry point
├── main.py             # core Q&A pipeline
├── config.py           # model, token limits, daily budget
├── modes.py            # response formats per mode
├── snapshot.py         # incremental codebase indexer
├── graph.py            # AST dependency graph
├── git_utils.py        # git diff utilities
├── context_loader.py   # loads README + ranked snapshot
├── client_claude.py    # Anthropic SDK client
├── client_openai.py    # OpenAI client (fallback)
├── logger.py           # usage + cost tracking
├── display.py          # terminal output
├── utils.py            # output compression
├── install.sh          # global CLI installer
└── .env.example        # API key template
```

Session orchestration components (in development):
```
askr/
├── daemon/             # session monitor + forecast engine
├── hooks/              # Claude Code hook scripts
└── state/              # project state files (per repo)
```

---

## Limitations (Current)

- Snapshot quality depends on LLM file summaries
- AST graph is static, not runtime
- macOS only for clipboard (`pbcopy`)
- Session orchestration not yet shipped

---

## Building in Public

Following development on [Twitter/X](https://x.com) — real usage, real numbers, real problems.

Contributions welcome. Open an issue or PR.
