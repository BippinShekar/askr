const vscode = require('vscode');
const fs     = require('fs');
const path   = require('path');
const os     = require('os');
const cp     = require('child_process');

const STATS_DIR         = path.join(os.homedir(), '.config', 'askr', 'stats');
const NOTIFICATION_PATH = path.join(os.homedir(), '.config', 'askr', 'notification.json');
const POLL_MS = 5000;

// Single-quote shell escaping — wrap in quotes, replace any literal ' with '\''.
function shellQuote(s) {
  return `'${String(s).replace(/'/g, `'\\''`)}'`;
}

// Runs a plain `askr ...` command with no visible terminal and no focus
// steal (2026-08-15) — createTerminal()+show() used to yank the user into a
// brand-new panel just to run a one-line, non-interactive command (Keep/
// Discard, Approve/Discard), leaving them stranded away from whatever they
// were actually doing. -l (login shell) matches lifecycle.py's own
// _patch_path() fix for the same problem on the Python side: a GUI-launched
// app (Cursor.app) doesn't inherit the interactive shell PATH that a real
// terminal would, so `askr` can 404 without it.
function runAskrSilently(args, opts = {}) {
  const command = 'askr ' + args.map(shellQuote).join(' ');
  cp.execFile('/bin/zsh', ['-l', '-c', command], { cwd: opts.cwd, timeout: 15000 }, (err) => {
    if (err) {
      vscode.window.showWarningMessage(`Askr: "${command}" failed — ${err.message}`);
    } else if (opts.successMessage) {
      vscode.window.showInformationMessage(opts.successMessage);
    }
  });
}

function latestStatsPath() {
  // No way to know which session_id belongs to "the chat the user is looking
  // at" from a VS Code status bar item — there's no per-terminal hook here,
  // unlike the CLI statusLine (which Claude Code feeds a real session_id on
  // stdin). So this just shows whichever session wrote most recently,
  // project-agnostic, the way it worked before per-project scoping was added.
  try {
    const files = fs.readdirSync(STATS_DIR).filter(f => f.endsWith('.json'));
    if (files.length === 0) return null;
    return files
      .map(f => path.join(STATS_DIR, f))
      .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
  } catch {
    return null;
  }
}

// Colours — applied to the entire status bar item
const COLOR_OK   = '#98c379';  // green
const COLOR_WARN = '#e5c07b';  // amber
const COLOR_HIGH = '#e06c75';  // red-orange
const COLOR_CRIT = '#ff5555';  // bright red
const COLOR_IDLE = '#6b7280';  // grey — no active session

function severityColor(pct) {
  if (pct >= 65) return COLOR_CRIT;   // checkpoint fires here
  if (pct >= 50) return COLOR_HIGH;   // getting full
  if (pct >= 35) return COLOR_WARN;
  return COLOR_OK;
}

function resetCountdown(isoStr) {
  try {
    const remainMs = new Date(isoStr) - Date.now();
    if (remainMs <= 0) return 'resets now';
    const h = Math.floor(remainMs / 3_600_000);
    const m = Math.floor((remainMs % 3_600_000) / 60_000);
    return h > 0 ? `resets in ${h}h ${m}m` : `resets in ${m}m`;
  } catch {
    return null;
  }
}

function shortCountdown(isoStr) {
  try {
    const remainMs = new Date(isoStr) - Date.now();
    if (remainMs <= 0) return '↺now';
    const h = Math.floor(remainMs / 3_600_000);
    const m = Math.floor((remainMs % 3_600_000) / 60_000);
    return h > 0 ? `↺${h}h${String(m).padStart(2, '0')}m` : `↺${m}m`;
  } catch {
    return null;
  }
}

function buildLabel(ctxPct, quotaPct, quotaResetIso, isLive, ctxLabel) {
  // Format: "askr  quota 32% ↺4h10m  chat 68%"
  // Warnings appended when either hits 80%+
  const parts = ['askr'];

  // Quota section — most important (causes waits when exhausted)
  if (quotaPct !== null) {
    const warn = quotaPct >= 90 ? ' ⚠' : quotaPct >= 80 ? ' !' : '';
    const reset = quotaResetIso ? (' ' + shortCountdown(quotaResetIso)) : '';
    parts.push(`quota ${quotaPct.toFixed(0)}%${warn}${reset}`);
  }

  // Context section — per-chat window
  const ctxWarn = ctxLabel === 'checkpoint' ? ' ⚠' : ctxLabel === 'getting full' ? ' !' : '';
  parts.push(`chat ${ctxPct}%${ctxWarn}`);

  // Stale indicator
  if (!isLive) parts.push('…');

  return parts.join('  ');
}

function buildTooltip(s, ctxPct, isLive) {
  const ctxTokens = (s.context_tokens  || 0).toLocaleString();
  const ctxWindow = (s.context_window  || 200_000).toLocaleString();
  const ctxLabel  = s.context_label    || 'ok';
  const quotaPct  = s.quota_pct        ?? null;
  const quota7d   = s.quota_7d_pct     ?? null;
  const resetIso  = s.quota_reset_at   || null;
  const model     = s.model            || 'claude';
  const turns     = s.turns            || 0;

  const statusLine = isLive ? '**Active session**' : '**No active session** — stats from last open chat';

  const ctxAlerts = {
    'checkpoint':   '\n\nCheckpointing now — askr saves state and opens a new chat.',
    'getting full': '\n\nPast 50%. Askr checkpoints at 65% to buffer extended-thinking turns.',
  };
  const ctxAlert = ctxAlerts[ctxLabel] || '';

  let quotaBlock = '';
  if (quotaPct !== null) {
    const resetStr  = resetIso ? resetCountdown(resetIso) : null;
    const resetLine = resetStr ? `\n\n${resetStr} (5-hour Anthropic window)` : '';
    const q7dLine   = quota7d !== null ? `\n\n7-day usage: **${quota7d.toFixed(0)}%**` : '';
    const qAlert    = quotaPct >= 90
      ? '\n\nAt limit — askr will checkpoint and wait for reset.'
      : quotaPct >= 80
      ? '\n\nApproaching limit — checkpoint will fire at 90%.'
      : '';
    quotaBlock = `\n\n---\n\n**Session quota: ${quotaPct.toFixed(0)}% used**${q7dLine}${resetLine}${qAlert}`;
  } else {
    quotaBlock = '\n\n---\n\n*Session quota: loading...*';
  }

  const md = new vscode.MarkdownString(
    `**Askr** — Claude Code session tracker\n\n`
    + `${statusLine}\n\n`
    + `---\n\n`
    + `**This chat: ${ctxPct}% full** (${ctxTokens} / ${ctxWindow} tokens)\n\n`
    + `Each new chat starts at 0%. Askr checkpoints at 65% — extended thinking can add 40-80K tokens per turn, so we fire early to avoid Claude auto-compacting first.`
    + ctxAlert
    + `\n\n${turns} turns · ${model}`
    + quotaBlock
    + `\n\n---\n\n*Click to run \`askr status\` in terminal*`
  );
  md.isTrusted = true;
  return md;
}

// Cache of the last successfully-read stats, keyed by nothing (single project per
// window). A transient read failure — the Python side writes stats files with a
// plain open()+json.dump (not atomic: temp file + rename), so the extension's 5s
// poll can catch a half-written file mid-write and get a JSON parse error, or the
// file can be deleted out from under it by the daemon's cleanup — must NOT blank
// the status bar. It should keep showing the last known-good reading, greyed out,
// until a fresh read succeeds. Hiding on every transient hiccup is what made the
// indicator "vanish" for no reason.
let _lastGoodResult = null;

function readStats() {
  try {
    const statsPath = latestStatsPath();
    if (!statsPath) return _lastGoodResult;
    const raw     = fs.readFileSync(statsPath, 'utf8');
    const s       = JSON.parse(raw);
    const staleMs = Date.now() - fs.statSync(statsPath).mtimeMs;

    if (staleMs > 7_200_000) {
      // Genuinely stale (no session in 2h+) — let it go, not a transient failure.
      _lastGoodResult = null;
      return null;
    }

    const ctxPct       = Math.round((s.context_pct || 0) * 100);
    const ctxLabel     = s.context_label  || 'ok';
    const quotaPct     = s.quota_pct      ?? null;
    const quotaResetIso = s.quota_reset_at || null;
    const isLive       = staleMs < 120_000;

    // Colour driven by whichever metric is more critical
    const maxPct = Math.max(ctxPct, quotaPct ?? 0);
    const color  = isLive ? severityColor(maxPct) : COLOR_IDLE;

    _lastGoodResult = {
      label:   buildLabel(ctxPct, quotaPct, quotaResetIso, isLive, ctxLabel),
      color,
      tooltip: buildTooltip(s, ctxPct, isLive),
    };
    return _lastGoodResult;
  } catch {
    // Transient read/parse failure (write race, file deleted mid-poll) — keep
    // showing the last known-good reading instead of hiding the item.
    return _lastGoodResult;
  }
}

// Best-effort terminal-content reading (2026-08-10, generalized 2026-08-11).
// There's no VS Code API to read a terminal's rendered content directly —
// sendText() (used everywhere below to launch companions) is write-only, and
// the proposed onDidWriteTerminalData API needs --enable-proposed-api, not
// viable for a normally-installed extension. This uses only stable APIs:
// select-all + copy-selection on the given terminal, then reads the copied
// scrollback back off the system clipboard as plain text. Fragile by
// nature — tied to whatever the terminal currently has rendered — so
// callers should fail closed on an unrecognized buffer, not guess.
//
// Visible side effect: this actually selects text in the target terminal
// (matching how a user would manually copy it) and briefly focuses it via
// show(true) — only call this against a terminal askr has a real reason to
// read right now, not speculatively.
async function readTerminalBuffer(term) {
  if (!term) return null;
  let original = null;
  try {
    original = await vscode.env.clipboard.readText();
  } catch { /* clipboard read is best-effort too — proceed without a restore point */ }
  try {
    term.show(true);
    await vscode.commands.executeCommand('workbench.action.terminal.selectAll');
    await vscode.commands.executeCommand('workbench.action.terminal.copySelection');
    return await vscode.env.clipboard.readText();
  } catch {
    return null;
  } finally {
    if (original !== null) {
      try { await vscode.env.clipboard.writeText(original); } catch { /* best-effort restore */ }
    }
  }
}

const DECOR_CHARS = /[─-╿]/g; // box-drawing block used to frame the input line

function extractPendingInput(buffer) {
  if (!buffer) return null;
  const lines = buffer.split(/\r?\n/).map(l => l.replace(DECOR_CHARS, '').trim());
  let end = lines.length - 1;
  while (end >= 0 && lines[end] === '') end--;
  if (end < 0) return null;
  let start = end;
  while (start >= 0 && lines[start] !== '' && !lines[start].startsWith('>')) start--;
  if (start < 0 || !lines[start].startsWith('>')) return null; // no confident prompt marker — don't guess
  const pending = lines.slice(start, end + 1)
    .map((l, i) => (i === 0 ? l.replace(/^>\s*/, '') : l))
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
  return pending || null;
}

// Companion-launch readiness probe (2026-08-18): sendText() is fire-and-
// forget, so the launch prompt used to be sent after a blind 4s setTimeout
// regardless of whether the `claude` CLI had actually finished booting.
// Confirmed live: under load (several companions spawning within the same
// few minutes) cold start routinely exceeds 4s, so the prompt+\r landed on
// a terminal that wasn't listening yet and was silently dropped — an idle
// companion terminal sitting on the banner with nothing typed into it, no
// error anywhere. Reuses readTerminalBuffer to poll for the empty ready
// prompt ('>' with nothing after it) before sending. Still sends
// unconditionally once the bounded wait is exhausted, so this degrades to
// the old blind-send behavior in the worst case rather than ever hanging.
function isPromptReady(buffer) {
  if (!buffer) return false;
  const lines = buffer.split(/\r?\n/).map(l => l.replace(DECOR_CHARS, '').trim());
  let end = lines.length - 1;
  while (end >= 0 && lines[end] === '') end--;
  return end >= 0 && lines[end] === '>';
}

async function waitForClaudeReady(terminal, checkDelaysMs = [6000, 5000]) {
  for (const delay of checkDelaysMs) {
    await new Promise(r => setTimeout(r, delay));
    if (isPromptReady(await readTerminalBuffer(terminal))) return;
  }
}

async function captureUnsentInput() {
  const term = vscode.window.activeTerminal;
  if (!term) return null;
  const buffer = await readTerminalBuffer(term);
  return extractPendingInput(buffer);
}

// Same-session rate-limit-resume feature, Stage 2 (2026-08-11): bridges
// Python's PID-based session tracking (which knows nothing about VS Code
// terminal objects) to vscode.window.terminals (which knows nothing about
// Claude session_ids). terminal.processId resolves to the PID of the SHELL
// running inside that terminal, not `claude` itself — Python walks the
// process-ancestor chain from the claude PID upward (lifecycle.
// _get_ancestor_pids) and hands over the resulting PID list; this just
// needs ANY of them to match, not a specific identified "shell" PID.
async function findTerminalByAncestorPids(ancestorPids) {
  if (!ancestorPids || !ancestorPids.length) return null;
  const wanted = new Set(ancestorPids);
  for (const term of vscode.window.terminals) {
    let pid;
    try {
      pid = await term.processId;
    } catch {
      continue;
    }
    if (pid && wanted.has(pid)) return term;
  }
  return null;
}

async function openContextCompanion(n) {
  const capturedInput = await captureUnsentInput();

  const goal = n.goal ? ` Picking up: ${n.goal}` : '';
  // last_summary (lifecycle._open_companion_session, 2026-08-10): a TL;DR of
  // what the companioned session last did, read back from the handover it
  // just wrote — so the user doesn't have to switch to the old session just
  // to see what it said before deciding whether to work in this new one.
  const summaryPreview = n.last_summary
    ? ` Last session: ${n.last_summary.length > 200 ? n.last_summary.slice(0, 200) + '…' : n.last_summary}`
    : '';
  const carriedOver = capturedInput ? ` Carried over what you were typing — continue it in the new window.` : '';
  vscode.window.showInformationMessage(`Askr: Context saved — opening a fresh companion session. Your current one keeps running.${goal}${summaryPreview}${carriedOver}`);

  const termOpts = { name: 'askr — new session' };
  if (n.project_path) termOpts.cwd = n.project_path;
  const terminal = vscode.window.createTerminal(termOpts);
  terminal.show();
  const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
    ? ` --allowedTools ${n.allowed_tools.join(',')}`
    : '';
  const defaultPrompt = n.prompt || 'Read the handover and start on the Next Action immediately. Work autonomously.';
  const launchPrompt = (capturedInput
    ? `Read the handover for full context, then continue with what the user was about to ask: ${capturedInput}`
    : defaultPrompt).replace(/"/g, '').replace(/`/g, '');
  if (n.last_summary) {
    // Shell-escape for a raw sendText echo: strip quotes/backticks (command
    // injection via the other launch prompts already strips these the same
    // way) plus $ and \ so nothing expands, and collapse to one line.
    const safeSummary = n.last_summary
      .replace(/[`"$\\]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
    if (safeSummary) terminal.sendText(`echo "askr — previous session: ${safeSummary}"`);
  }
  terminal.sendText(`claude${toolsFlag}`);
  waitForClaudeReady(terminal).then(() => {
    terminal.sendText(launchPrompt, false);
    terminal.sendText('\r', false);
  });
}

function checkNotification() {
  try {
    if (!fs.existsSync(NOTIFICATION_PATH)) return;
    const n = JSON.parse(fs.readFileSync(NOTIFICATION_PATH, 'utf8'));
    if (n.shown) return;

    // If the notification targets a specific project, only handle it in the
    // matching workspace. Other windows skip it; Terminal.app fallback fires
    // after 6s if no window claims it.
    const currentWorkspace = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || '';
    if (n.project_path && currentWorkspace && n.project_path !== currentWorkspace) return;

    n.shown = true;
    fs.writeFileSync(NOTIFICATION_PATH, JSON.stringify(n));

    if (n.type === 'context') {
      // Capture BEFORE anything else touches focus/clipboard — creating and
      // showing the new terminal below would make it the active one, and by
      // then whatever the user had typed into the old terminal's prompt is no
      // longer reachable via activeTerminal.
      openContextCompanion(n);
    } else if (n.type === 'compaction_prevented') {
      // Emergency PreCompact kill (askr/hooks/pre_compact.py) — the session
      // was stopped before Claude Code's own compaction could compress it.
      // Deduped per session_id on the Python side, so this fires once per
      // affected session, not once per repeated PreCompact trigger.
      vscode.window.showInformationMessage(`Askr: ${n.message}`);
      if (n.opened_companion) {
        const termOpts = { name: 'askr — companion (full memory)' };
        if (n.project_path) termOpts.cwd = n.project_path;
        const terminal = vscode.window.createTerminal(termOpts);
        terminal.show();
        const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
          ? ` --allowedTools ${n.allowed_tools.join(',')}`
          : '';
        const launchPrompt = (n.prompt || 'Read the handover and continue immediately. Work autonomously.').replace(/"/g, '').replace(/`/g, '');
        terminal.sendText(`claude${toolsFlag}`);
        waitForClaudeReady(terminal).then(() => {
          terminal.sendText(launchPrompt, false);
          terminal.sendText('\r', false);
        });
      }
    } else if (n.type === 'quota') {
      // Quota trigger's own richer message (lifecycle._write_notification) —
      // no terminal to open here: the daemon opens the companion itself once
      // the account's quota actually resets, this is purely informational.
      vscode.window.showInformationMessage(`Askr: ${n.message}`);
    } else if (n.type === 'quota_exhausted_wait') {
      // Same-session rate-limit-resume, step 1 (2026-08-12): quota is
      // confirmed genuinely exhausted via askr's own ground-truth API poll
      // (lifecycle._wait_until_quota_near_exhausted) — not a guess. Send
      // Escape into the exact terminal running that session, proven
      // equivalent to manually selecting "Stop and wait for limit to
      // reset" (see the compaction_prevented history above). Safe even if
      // the menu hasn't rendered yet: at a normal idle prompt, Escape is a
      // harmless no-op.
      vscode.window.showInformationMessage(`Askr: ${n.message}`);
      findTerminalByAncestorPids(n.ancestor_pids).then(term => {
        if (term) term.sendText('\x1b', false);
        else console.warn(`Askr: quota_exhausted_wait found no terminal matching ancestor_pids ${JSON.stringify(n.ancestor_pids)} — Escape not sent (harmless: Claude Code shows its own rate-limit prompt regardless)`);
      });
    } else if (n.type === 'quota_resume_cont') {
      // Same-session rate-limit-resume, step 2: reset genuinely arrived with
      // no premature activity detected (lifecycle._watch_for_premature_activity) —
      // resume the same session's in-flight work in place instead of only
      // ever handing the user a fresh companion.
      //
      // Found 2026-09-04: findTerminalByAncestorPids can miss (terminal
      // closed/reopened, window reloaded, or a Cursor "Agents" panel terminal
      // that isn't a real vscode.window.Terminal). Previously this failed
      // completely silently — the daemon writes the notification and marks
      // itself done with no ack from this side, so a miss here meant the
      // session sat stuck at the rate-limit prompt forever with zero
      // indication anything went wrong. This is the one step that actually
      // has to land, so a miss must be loud and tell the user what to type.
      vscode.window.showInformationMessage(`Askr: ${n.message}`);
      findTerminalByAncestorPids(n.ancestor_pids).then(term => {
        if (term) {
          term.sendText(n.resume_text || 'cont', true);
        } else {
          vscode.window.showWarningMessage(
            `Askr: quota reset, but couldn't find the original terminal to auto-resume it — type "${n.resume_text || 'cont'}" there yourself to continue.`
          );
          console.warn(`Askr: quota_resume_cont found no terminal matching ancestor_pids ${JSON.stringify(n.ancestor_pids)} — '${n.resume_text || 'cont'}' not sent`);
        }
      });
    } else if (n.type === 'goal_launch') {
      const goal = n.goal || '';
      const termOpts = { name: `askr — ${goal.slice(0, 40)}` };
      if (n.project_path) termOpts.cwd = n.project_path;
      const terminal = vscode.window.createTerminal(termOpts);
      terminal.show();
      const safeGoal = goal.replace(/"/g, '').replace(/`/g, '');
      const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
        ? ` --allowedTools ${n.allowed_tools.join(',')}`
        : '';
      const launchPrompt = n.prompt
        ? n.prompt.replace(/"/g, '').replace(/`/g, '')
        : `Read the handover and work on this goal autonomously: ${safeGoal}`;
      terminal.sendText(`claude${toolsFlag}`);
      waitForClaudeReady(terminal).then(() => {
        terminal.sendText(launchPrompt, false);
        terminal.sendText('\r', false);
      });
      vscode.window.showInformationMessage(`Askr: Starting session — ${goal.slice(0, 80)}`);
    } else if (n.type === 'goal_check') {
      // Stale inferred goals — ask user what to do, log the outcome
      const goals = (n.goals || []).map(g => g.text);
      const preview = goals.slice(0, 2).map(g => `"${g.length > 40 ? g.slice(0, 40) + '…' : g}"`).join(', ');
      const summary = goals.length === 1
        ? `Goal stale for ${n.goals[0].hours}h: "${goals[0]}"`
        : `${goals.length} goals stale 6h+: ${preview}`;
      vscode.window.showWarningMessage(
        `Askr: ${summary}`,
        'Mark Done', 'Discard', 'Keep'
      ).then(action => {
        if (!action || action === 'Keep') return;
        const sub = action === 'Mark Done' ? 'done' : 'discard';
        goals.forEach(g => runAskrSilently(['goal', sub, g]));
      });
    } else if (n.type === 'behavior_confirm') {
      // High-confidence behavioral preference(s) detected from this session's
      // conversation (askr Phase 3.9). Ask the user before touching CLAUDE.md —
      // if this notification is never claimed, checkpoint.py's fallback worker
      // auto-persists it headless after FALLBACK_DELAY_SECONDS and posts to
      // Discord instead. Mirrors goal_check's aggregate Keep/Discard-over-a-
      // batch pattern.
      const rules = n.rules || [];
      const preview = rules
        .map(r => `"${r.rule.length > 60 ? r.rule.slice(0, 60) + '…' : r.rule}"`)
        .join(', ');
      const summary = rules.length === 1
        ? `Detected preference: ${preview}`
        : `Detected ${rules.length} preferences: ${preview}`;
      vscode.window.showInformationMessage(
        `Askr: ${summary}`,
        'Keep', 'Discard'
      ).then(action => {
        if (!action) return;  // dismissed — stays in `askr prefs pending` untouched
        rules.forEach(r => {
          if (action === 'Keep') {
            runAskrSilently(['prefs', 'keep', r.rule, '--scope', r.scope || 'project']);
          } else {
            runAskrSilently(['prefs', 'discard', r.rule]);
          }
        });
      });
    } else if (n.type === 'reload_extension') {
      vscode.window.showInformationMessage(
        'Askr updated — reload the window to activate new changes.',
        'Reload Now'
      ).then(action => {
        if (action === 'Reload Now') {
          vscode.commands.executeCommand('workbench.action.reloadWindow');
        }
      });
    } else if (n.type === 'direction_proposal') {
      // High-confidence direction from a talk-only (research/strategy) session.
      // Don't auto-launch — let the user decide: run it now, queue it, or drop it.
      const preview = n.direction ? n.direction.slice(0, 120) : n.message;
      vscode.window.showInformationMessage(
        `Askr: ${preview}`,
        'Start Now',
        'Add to Goals',
        'Dismiss'
      ).then(action => {
        if (!action || action === 'Dismiss') return;
        if (action === 'Add to Goals') {
          // Just queues it — no interactive session to show here. The daemon
          // auto-launches it later on its own schedule, which fires its own
          // goal_launch notification (and its own terminal) when it actually starts.
          const dir = (n.direction || preview).slice(0, 120);
          runAskrSilently(['goal', 'add', dir], { cwd: n.project_path, successMessage: 'Askr: added to goals' });
        } else {
          // Start Now — this genuinely opens an interactive Claude session,
          // so a visible, focused terminal is the right call here.
          const termOpts = { name: 'askr', ...(n.project_path ? { cwd: n.project_path } : {}) };
          const terminal = vscode.window.createTerminal(termOpts);
          terminal.show();
          const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
            ? ` --allowedTools ${n.allowed_tools.join(',')}`
            : '';
          const safePrompt = (n.prompt || n.direction || '').replace(/"/g, '').replace(/`/g, '');
          terminal.sendText(`claude${toolsFlag}`);
          waitForClaudeReady(terminal).then(() => {
            terminal.sendText(safePrompt, false);
            terminal.sendText('\r', false);
          });
        }
      });
    } else if (n.type === 'direction_confirm' || n.type === 'direction_needed') {
      // Low-confidence or no direction signal — do NOT open a session automatically.
      // Ask the user what to work on; only open Claude once they provide a direction.
      const title = n.type === 'direction_needed'
        ? 'Askr: No direction found'
        : 'Askr: Direction unclear';
      vscode.window.showInputBox({
        title,
        prompt: n.message,
        value: n.direction || '',
        placeHolder: 'What should the next session work on?',
        ignoreFocusOut: true,
      }).then(input => {
        if (!input) return;  // user cancelled — no session, no tokens burned
        const termOpts = { name: 'askr — new session' };
        if (n.project_path) termOpts.cwd = n.project_path;
        const terminal = vscode.window.createTerminal(termOpts);
        terminal.show();
        const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
          ? ` --allowedTools ${n.allowed_tools.join(',')}`
          : '';
        const safeInput = input.replace(/"/g, '').replace(/`/g, '');
        terminal.sendText(`claude${toolsFlag}`);
        waitForClaudeReady(terminal).then(() => {
          terminal.sendText(safeInput, false);
          terminal.sendText('\r', false);
        });
      });
    } else if (n.type === 'guard_warning') {
      // Non-blocking by design (Phase 3.5) — informational only, no action needed.
      vscode.window.showWarningMessage(`Askr guard: ${n.summary || n.message}`);
    } else if (n.type === 'guard_approval_pending') {
      // Escape-hatch redesign (2026-08-15) — the write is HELD, not allowed.
      // Used to auto-pass through here after 2 blocks with only a Discord
      // message after the fact; confirmed in real use (twice) that two
      // retries isn't evidence a human ever reviewed the approach. The file
      // stays blocked until Approve/Discard actually runs.
      vscode.window.showWarningMessage(
        `Askr: ${n.message}`,
        'Approve', 'Discard'
      ).then(action => {
        if (!action) return;
        const sub = action === 'Approve' ? 'approve' : 'discard';
        const successMessage = action === 'Approve' ? 'Askr: approved' : 'Askr: discarded';
        runAskrSilently(['guard', sub, n.file_path], { successMessage });
      });
    } else if (n.type === 'billing_anomaly_alert') {
      // Same-session rate-limit-resume safety net (lifecycle.
      // _alert_premature_activity, 2026-08-11) — the only showErrorMessage
      // in this extension, reserved for the one notification type that
      // means a real, unintended billing action may have just happened.
      // Not dismiss-and-forget: re-shown every poll until the user opens
      // their Anthropic billing page, since a single toast is exactly the
      // kind of thing that gets missed when it matters most.
      vscode.window.showErrorMessage(
        `Askr: ${n.message}`,
        'Open Anthropic Billing'
      ).then(action => {
        if (action === 'Open Anthropic Billing') {
          vscode.env.openExternal(vscode.Uri.parse('https://console.anthropic.com/settings/billing'));
        } else {
          n.shown = false; // not acknowledged — surface again next poll
          try { fs.writeFileSync(NOTIFICATION_PATH, JSON.stringify(n)); } catch {}
        }
      });
    } else if (n.type === 'task_approval_pending') {
      // Phase 5 approval gate — a teammate's queued task is held because this
      // session has dangerous permissions (--dangerously-skip-permissions,
      // unrestricted Bash, or an rm pattern in permissions.allow).
      const dev = n.developer || '';
      const count = (n.tasks || []).length;
      vscode.window.showWarningMessage(
        `Askr: ${count} queued task(s) held for ${dev} — ${(n.reasons || []).join('; ')}`,
        'Approve', 'Discard'
      ).then(action => {
        if (!action) return;
        const sub = action === 'Approve' ? 'approve' : 'discard';
        const successMessage = action === 'Approve' ? 'Askr: approved' : 'Askr: discarded';
        runAskrSilently(['task', sub, dev], { successMessage });
      });
    } else {
      // Any notification type without a dedicated case above — just inform.
      vscode.window.showInformationMessage(`Askr: ${n.message}`);
    }
  } catch {}
}

function activate(context) {
  const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 1000);
  item.command = 'askr.openStatus';

  context.subscriptions.push(
    vscode.commands.registerCommand('askr.openStatus', () => {
      const terminal = vscode.window.createTerminal({ name: 'askr' });
      terminal.show();
      terminal.sendText('askr status');
    })
  );

  function refresh() {
    checkNotification();
    const result = readStats();
    if (result) {
      item.text    = result.label;
      item.color   = result.color;
      item.tooltip = result.tooltip;
      item.show();
    } else {
      item.hide();
    }
  }

  refresh();
  const timer = setInterval(refresh, POLL_MS);
  context.subscriptions.push(item);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });

  try {
    if (!fs.existsSync(STATS_DIR)) fs.mkdirSync(STATS_DIR, { recursive: true });
    const watcher = fs.watch(STATS_DIR, (_, filename) => {
      if (filename && filename.endsWith('.json')) refresh();
    });
    context.subscriptions.push({ dispose: () => watcher.close() });
  } catch {}
}

function deactivate() {}

module.exports = { activate, deactivate };
