# Quota-Exhaustion Auto-Resume — How It Actually Works

Reference doc for the three pieces flagged before the launch/demo recording:
Escape-key menu automation, same-session auto-continuation, and daemon logs.
All of this is implemented and live, not a design-only decision — file/line
citations below point at the real code.

## 1. Escape-key quota-reset menu automation

**Problem:** when the account's real 5-hour usage limit is hit, Claude Code
shows a menu ("Stop and wait for limit to reset" / "Continue with extra
usage" / "Upgrade plan"). Left alone, the session sits there until a human
picks an option.

**How askr picks it for you:** binary analysis of Claude Code confirmed that
sending a bare Escape keystroke and manually selecting "Stop and wait" both
resolve to the same internal handler (`der()`) — so Escape is a
position-independent way to select "wait for reset" regardless of menu
ordering, without parsing menu text or risking a remote feature-flag reorder
breaking arrow-key navigation.

**Ground truth, not a guess:** askr does not infer exhaustion from hook
silence. `_wait_until_quota_near_exhausted()`
(`askr/session/lifecycle.py:621`) polls the real usage API directly via
`askr.session.usage_api.get_quota_status()` until `five_hour_pct >=
QUOTA_NOTIFY_TRIGGER` (99.0%, `lifecycle.py:614`) or the reset time passes.

**Send path:**
- `_execute_quota_trigger()` (`lifecycle.py:1363-1394`) resolves the live
  session's PID via `_find_session_pid()`, then walks its ancestor
  processes with `_get_ancestor_pids()` to find the actual terminal hosting
  it — necessary because Claude Code can spawn multiple terminal instances,
  and title/index matching doesn't survive renames.
- It writes a `quota_exhausted_wait` notification
  (`_write_terminal_action_notification`, `lifecycle.py:1386-1391`) with the
  ancestor PID list.
- `extension.js:373-385` (Cursor/VS Code extension) picks this up,
  resolves the terminal via `findTerminalByAncestorPids(n.ancestor_pids)`,
  and calls `term.sendText('\x1b', false)` — the actual Escape send.
  Safe to fire even if the menu hasn't rendered yet: at a normal idle
  prompt, Escape is a no-op.

**Stage status** (per `askr_state/decisions.jsonl`'s 5-stage plan —
instrumentation, PID→terminal bridge, wait-for-real-data, wire automation,
safety-net detection): all five are implemented. Stage 5 is the
premature-activity watch below.

## 2. Auto-continuation of the same session

Once Escape is sent, askr doesn't just hand the user a fresh companion and
walk away — it tries to resume the **same session** in place:

1. **Safety net first** — `_watch_for_premature_activity()`
   (`lifecycle.py:676-729`) polls the transcript file's mtime every 20s
   (`_PREMATURE_ACTIVITY_POLL_SECS`) between now and the real reset time.
   There's no stable API to read terminal buffer contents, so this uses an
   out-of-band signal instead: if the transcript starts growing *before*
   the real reset time, that's proof a spending path ("extra usage" /
   "upgrade") got selected instead of "wait for reset" — a real billing
   event, not a UX hiccup. It fires `_alert_premature_activity()`
   (`lifecycle.py:732`) on every channel (log, notification, voice)
   unconditionally — this is the one alert in the file with no rate
   limiting, deliberately.
2. **Clean resume** — if reset arrives with no premature activity,
   `_execute_quota_trigger()` (`lifecycle.py:1407-1416`) writes a
   `quota_resume_cont` notification with `resume_text: "cont"`.
   `extension.js:386-394` sends that text into the same terminal via
   `term.sendText(n.resume_text || 'cont', true)` — literally typing
   `cont` and pressing enter into the now-idle session.
3. **Fallback** — if the PID can't be resolved, the ancestor walk comes up
   empty, or the safety net catches premature activity, askr falls back to
   the pre-existing behavior: `_wait_for_reset()` (`lifecycle.py:599`)
   sleeps until reset, then opens a fresh companion via `_start_claude()`
   (`lifecycle.py:1436`) — the user's original session is never killed by
   this path; askr only ever adds a session, never removes one, on this
   fallback branch.

Both outcomes emit an event (`companion_spawned` for the fallback,
`_write_resumed_marker("quota", ...)` for a clean same-session resume) plus
a Discord notification (`_notify_discord_resumed`).

## 3. Daemon logs

- **Location:** `~/.config/askr/daemon.log` (`_LOG_PATH`,
  `lifecycle.py:74`).
- **Mechanism:** the daemon never opens this file itself. `_log()`
  (`lifecycle.py:186-188`) just prints timestamped lines to stdout;
  `~/Library/LaunchAgents/com.askr.daemon.plist` sets both
  `StandardOutPath` and `StandardErrorPath` to that same file, so launchd
  does the actual redirect. `KeepAlive: true` in the plist means the daemon
  restarts automatically on any clean exit — including the deliberate
  self-restart the daemon does when it detects its own source files
  changed (source self-watch, see `session_start.py`/`lifecycle.py`
  history).
- **What's in it:** every `_log()` call across the daemon loop — session
  active/idle transitions, per-project trigger evaluations, and, since the
  independent-poll fix, one line per quota poll:
  `Trigger B (independent poll): quota=NN.N% (real API) [project_path]`
  (`lifecycle.py:2537`).
- **The independent quota poll** (`_poll_independent_quota_and_fire`,
  `lifecycle.py:2491-2559`), called from `run_daemon()`'s main loop
  (`lifecycle.py:2615-2617`) on **every** iteration regardless of whether
  any project looks active: this is the fix for a confirmed-live bug where
  the old per-project trigger only refreshed via `PostToolUse` hooks, so
  once the account actually hit 100% no more tool calls happened and the
  per-project stats file froze at a stale value (often ~84%), and the
  trigger could never cross its own threshold. The independent poll hits
  the live usage API directly on a 60s cadence
  (`_INDEPENDENT_QUOTA_POLL_SECS = 60`, `lifecycle.py:2488`, matched to
  `QUOTA_NOTIFY_POLL_SECS`) and fires `_execute_quota_trigger` for every
  affected project regardless of that project's own stats freshness,
  reusing the existing per-reset-window dedup
  (`_reset_window_already_triggered`) so it can't double-fire against the
  per-project path.
- **Daemon loop structure:** `run_daemon()` (`lifecycle.py:2562`) —
  single-instance PID guard, loads seven disk-backed state dicts (trigger
  timestamps, companioned sessions, quota-warned/-triggered windows, idle
  triggers, session-first-seen, session-parent lineage), then loops
  forever: active/idle transition logging → independent quota poll (always)
  → if active, full per-project trigger scan (`_read_all_stats()`, highest
  context first).

## Live verification, 2026-08-15 (quota at 74%, approaching real limit)

Cross-checked against the running system while quota was genuinely climbing,
not just static code reading:

- **Daemon liveness — confirmed.** `launchctl list` shows `com.askr.daemon`
  running (exit status 0). `daemon.log` is being written every ~15s with
  fresh `ctx=/quota=` lines for every active project, matching the
  independently-reported 74% exactly.
- **Threshold config — confirmed correct.** `QUOTA_WARNING_TRIGGER = 75.0`
  (`lifecycle.py:146`), `QUOTA_TRIGGER = 90.0` (`lifecycle.py:145`),
  `QUOTA_NOTIFY_TRIGGER = 99.0` (`lifecycle.py:614`) — three-phase flow
  intact.
- **Dedup state — clean.** `~/.config/askr/quota_triggered_windows.json` is
  `[]` (last touched 2026-08-11) — nothing stale would suppress a fire for
  the current reset window.
- **KNOWN GAP — `_find_session_pid`'s primary lookup is unreliable.**
  `lsof -t <transcript_path>` against this exact live, actively-writing
  session returned empty 5/5 consecutive tries. Claude Code evidently opens
  the transcript file per-message rather than holding it open continuously,
  so the "precise, multi-session-safe" lsof method the docstring
  (`lifecycle.py:436-449`) claims is in practice dead weight — every call
  silently falls through to the pgrep+cwd fallback
  (`lifecycle.py:466-485`).
  - That fallback **does** resolve correctly today, because there is
    currently exactly one `claude` process per project cwd.
  - It **cannot disambiguate two sessions sharing the same project
    directory** — which is exactly the state a companion-spawn creates.
    If quota is hit again while a companion is already open in the same
    project, the fallback could match either PID, potentially walking
    ancestors from the wrong (already-idle) session and sending Escape
    into the wrong terminal. `extension.js`'s Escape-into-idle-terminal
    is a documented no-op, so this fails *silently* rather than erroring —
    the actually-blocked session would just stay stuck with no signal
    anything went wrong.
  - **Action before relying on this for a same-project companion scenario:**
    either fix `_find_session_pid` to reliably resolve the right PID when
    the transcript file isn't held open (e.g. match on cwd + newest
    stats-file `session_id` correlation instead of lsof), or explicitly
    test the two-sessions-same-project case before the demo rather than
    assuming today's single-session behavior generalizes.

## What's still open (per the 8ed7cfb6 handover, 2026-08-15)

- Run the overnight autonomous orchestrator test and query `events.jsonl`
  to validate the full detect → Escape → wait → `cont` flow end-to-end
  against a real exhaustion event (only individually-verified pieces so
  far, not a confirmed live run of the whole chain).
- Monitor `daemon.log` over the next 7 days for Trigger B fire patterns and
  quota=100% detection latency.
- Confirm Stage 4/5 (Escape send, safety net, `cont` resume) actually fire
  correctly against a real quota exhaustion, not just unit-level code
  inspection.
