# askr

**Autonomous session orchestration for Claude Code. Built for developers who ship with Claude.**

Three problems. One tool.

1. **Session exhaustion** — Claude hits context or quota limits mid-task. Work stops. Recovery is manual.
2. **Team drift** — your co-founder doesn't know what you built last night. You explain it again. On Slack. Like animals.
3. **Implementation holes** — Claude sounds confident, you approve the approach, an hour later you're reverting because it conflicted with something already built.

Askr fixes all three. It monitors your sessions, checkpoints before Claude degrades, resumes automatically, keeps project state in git so both developers always start informed, and catches architectural mistakes before the first file is touched.

> Claude may stop. Work must not. And what it builds must be right.

---

## What's Shipped

### Session Orchestration (Phase 2 ✅)

Askr runs a background daemon that watches your Claude Code session via the JSONL transcript file. Two triggers:

**Trigger A: Context near compaction (~90%)**
```
Context window approaching limit
→ Askr intercepts before lossy auto-compact fires
→ Writes handover.md with full session state
→ Commits + pushes to git
→ Stops session, starts new one immediately
→ Claude continues from exact next step
```

**Trigger B: Quota window nearly exhausted**
```
5-hour usage window running low
→ Askr checkpoints + commits
→ Stops session
→ Waits for exact reset time (derived from JSONL first-entry + 5h)
→ Auto-resumes after reset
→ Claude continues from exact next step
```

### Project State (Phase 1 ✅)

Structured markdown files committed to git on every checkpoint. Both developers pull this state at session start. Claude reads it automatically.

| File | What it tracks |
|---|---|
| `handover_<dev>.md` | Last session's objective, next step, files changed |
| `current_task_<dev>.md` | Last 5 user prompts with timestamps |
| `decisions.md` | Append-only timestamped decision log |
| `implementation_state.md` | Per-developer in-progress + completed work |
| `architecture.md` | System overview, modules, patterns |
| `goals.md` | Today's goals, backlog, done — tracked across sessions |

### Goals (auto-managed)

Goals can be set manually or inferred automatically:

- **At session start**: if today has no goals, Haiku reads your last handover and suggests 1-2 goals, added automatically
- **During session**: Claude sees your goals in context and works toward them
- **At session end**: Haiku infers which goals were completed based on what was actually built

### Always-On Daemon + caffeinate

`askr init` installs a launchd service (`com.askr.daemon`) that starts at login and runs silently in the background. No `askr launch` needed.

**What it does automatically:**
- Detects when a Claude Code session starts (by watching `session_stats.json` freshness)
- Starts `caffeinate -i` — prevents system idle sleep, allows display to dim
- Monitors context and quota thresholds every 30s
- Fires Trigger A or B when thresholds are crossed
- Releases caffeinate when the session ends or goes idle

**Battery note:** `caffeinate -i` cannot prevent sleep when the lid is closed on battery. Plug in for overnight runs. Askr warns you at `askr init` and when a session starts on battery.

```bash
askr launch           # show daemon status + current session
askr launch --stop    # kill daemon manually (restarts at next login)
askr launch --restart # force restart now
```

To disable permanently:
```bash
launchctl unload ~/Library/LaunchAgents/com.askr.daemon.plist
```

### IDE Status Bar

Live context usage shown in Cursor / VS Code bottom status bar:

```
askr 45% ↺3h42m          ← normal (green)
askr 76% ↺2h10m          ← high usage (amber)
askr 88% ↺1h30m !        ← near limit (red)
askr 93% ↺0h55m ⚠        ← checkpoint imminent (bright red)
askr 67% ↺1h20m …        ← stale, no active session (grey)
```

Hover shows: current chat context (tokens used / 200k), quota reset countdown, and what each number means.

### The `ask` CLI

During quota resets, `ask` fills dead time with grounded answers from your codebase:

```bash
ask "cto: best way to structure the auth layer?"
ask "debug: getting a 401 on every login attempt"
ask "quick: what does buildContextInjection return?"
```

Fast (~$0.001/query), grounded in your codebase snapshot, works from any directory.

---

## Install

```bash
git clone https://github.com/BippinShekar/askr.git
cd askr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# add ANTHROPIC_API_KEY to .env
bash install.sh
source ~/.zshrc
```

---

## Setup (per project)

```bash
cd ~/your-project
ask init       # index codebase — generates snapshot for architecture.md
askr init      # configure for this project, install hooks + IDE extension
```

`askr init` does in one step:
- Saves developer name + project path
- Generates `askr_state/architecture.md` from codebase snapshot (Haiku)
- Creates all state files from templates
- Installs Claude Code hooks (SessionStart, UserPromptSubmit, PostToolUse, Stop, PreCompact)
- Wires the statusLine command into `.claude/settings.json`
- Installs the status bar extension to `~/.cursor/extensions/` and `~/.vscode/extensions/`

Reload your IDE window after `askr init` to activate the status bar.

---

## Discord Notifications (optional)

Askr can send checkpoints, goal completions, and session events to a Discord channel. Solo developers and teams both supported.

### Solo setup (personal server)

1. Create a Discord server (e.g. "askr notifications")
2. Go to **Server Settings → Integrations → Webhooks → New Webhook**
3. Name it, select the channel (e.g. `#general`), click **Copy Webhook URL**
4. Add to your `.env`:
   ```
   ASKR_DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
   ```

### Team setup (shared channel)

1. In your shared Discord server, create a `#dev-activity` channel
2. Go to **Channel Settings → Integrations → Webhooks → New Webhook**
3. Each developer adds that same webhook URL to their own `.env`

All team members' session events (checkpoints, goals completed, session resumes) post to the shared channel — a passive async standup feed. No duplicate notifications: each developer's askr instance posts its own events only.

### What gets posted

| Event | Message |
|---|---|
| Checkpoint (context/quota hit) | Trigger type, developer, timestamp |
| Session resumed | Reason + next goal |
| Goal completed | Goal text |
| Session ended | Goals completed + files changed (standup replacement) |
| Claude notification (HITL) | Forwarded overnight so you don't miss it |
| `askr report` | Full daily summary on demand |

---

## Commands

```bash
# Session
askr init                   # set up in this project
askr status                 # show current state + session context %
askr status --line          # one-line output for scripts / terminal

# Daemon (always-on via launchd — installed by askr init)
askr launch                 # show daemon status + current session
askr launch --stop          # kill daemon (restarts at next login)
askr launch --restart       # force restart now

# Goals
askr goals                  # show today, backlog, done
askr goal add "..."         # add a goal for today
askr goal add "..." --backlog   # add to backlog
askr goal done "..."        # mark a goal complete

# Notifications
askr report                 # send daily report to Discord (sessions, time saved, next goal)

# Codebase Q&A
ask "cto: ..."              # architectural decision
ask "ceo: ..."              # product/business framing
ask "debug: ..."            # bug fix (includes recent git diff)
ask "deep: ..."             # thorough explanation
ask "quick: ..."            # one-liner answer
ask "web: ..."              # live web search
ask init                    # index codebase
ask snap                    # force snapshot rebuild
ask log                     # show usage + cost this week
```

---

## Session Lifecycle

```
Developer opens Claude Code
         ↓
SessionStart hook fires
  → git pull (get teammate's latest state)
  → inject handover + goals into context
  → if no goals today: Haiku suggests from last handover
         ↓
Developer works with Claude
  → PostToolUse hook: updates implementation_state.md
                      writes session_stats.json for status bar
  → UserPromptSubmit hook: records last 5 prompts to current_task.md
         ↓
Daemon polls session_stats.json every 30s
  → context ≥ 90%  → Trigger A
  → quota window ≤ 30min → Trigger B
         ↓
On trigger: safe_pause check → checkpoint → git commit+push
  Trigger A: start new Claude immediately
  Trigger B: sleep until reset, then start new Claude
         ↓
New session starts
  → SessionStart fires again
  → Claude reads handover, continues from next step
```

---

## Project Structure

```
askr/                        # Python package
  cli/
    ask.py                   # ask command — codebase Q&A
    askr.py                  # askr command — session orchestration
  hooks/                     # Claude Code hook scripts
    session_start.py         # git pull + context injection + goal suggestion
    user_prompt_submit.py    # strip IDE tags, record last 5 prompts
    post_tool_use.py         # track activity + write session stats
    stop.py                  # generate handover, commit, push
    pre_compact.py           # emergency checkpoint fallback
    notification.py          # HITL stub (Discord in Phase 3)
  session/                   # session orchestration
    monitor.py               # read JSONL → context%, session start time
    forecast.py              # context label (ok/high/near limit/checkpoint)
    checkpoint.py            # handover + git commit+push, shared by stop + lifecycle
    lifecycle.py             # background daemon: poll, trigger, kill, resume
    safe_pause.py            # check git clean, no tests running, no active writes
  state/                     # state file management
    config.py                # developer name, project path
    writer.py                # write/append to all state files
    reader.py                # build context injection for Claude
    goals.py                 # goals CRUD + Haiku inference
    templates/               # markdown templates for state files
  qa/                        # ask CLI pipeline
    pipeline.py, snapshot.py, graph.py, context_loader.py, modes.py
  clients/
    claude.py                # Anthropic SDK client
    openai.py                # OpenAI fallback
  ide/
    vscode-extension/        # status bar extension (Cursor + VS Code)
      extension.js
      package.json
  utils/
    config.py, display.py, logger.py, env.py

askr_state/                  # project state data (committed to git)
  handover_<dev>.md
  current_task_<dev>.md
  decisions.md
  implementation_state.md
  architecture.md
  blockers.md
  goals.md
```

---

## Coming Next

### Phase 3 — Notifications + Morning Report
- Discord webhook notifications (checkpoint done, session resumed, goal completed)
- Morning report (sessions run, time saved, decisions made, goals completed)
- Time-saved analytics

### Phase 3.5 — Implementation Guard
- Pre-tool-use hook detects when Claude is about to start a significant implementation
- Haiku cross-checks the proposed approach against `architecture.md` and `handover.md`
- Flags architectural holes, missing dependencies, API mismatches — before the first file is touched
- Non-blocking: surfaces as an IDE popup and Discord warning, developer decides whether to proceed
- `guard_log.md` tracks every warning raised and what the developer chose to do

### Phase 4 — Public Launch
- `brew install askr`
- Polished README with GIF of status bar + morning report
- GitHub release + Twitter/X launch thread

---

## Limitations

- macOS only (uses `pbcopy` for clipboard, `lsof` for write detection)
- Quota reset time derived from JSONL session start + 5h (accurate but indirect)
- IDE status bar requires Cursor or VS Code; reload window after `askr init`
- Autonomous overnight mode requires `askr launch` to be running

---

## Building in Public

Following development on [Twitter/X](https://x.com) — real usage, real numbers, real problems.

Contributions welcome. Open an issue or PR.
