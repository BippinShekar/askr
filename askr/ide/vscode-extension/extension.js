const vscode = require('vscode');
const fs     = require('fs');
const path   = require('path');
const os     = require('os');

const STATS_DIR         = path.join(os.homedir(), '.config', 'askr', 'stats');
const NOTIFICATION_PATH = path.join(os.homedir(), '.config', 'askr', 'notification.json');
const POLL_MS = 5000;

function projectHashPrefix() {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath || '';
  return root.replace(/\//g, '-').replace(/^-/, '');
}

function projectStatsPath() {
  // Per-session files ({hash}_{session_id}.json) are what post_tool_use writes.
  // The legacy {hash}.json is reset to 0% on session start and never updated.
  // Pick the most recently modified file that matches this project's prefix.
  const hash = projectHashPrefix();
  try {
    const files = fs.readdirSync(STATS_DIR).filter(f =>
      f.endsWith('.json') && (f === hash + '.json' || f.startsWith(hash + '_'))
    );
    if (files.length > 0) {
      const newest = files
        .map(f => path.join(STATS_DIR, f))
        .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs)[0];
      return newest;
    }
  } catch {}
  return path.join(STATS_DIR, hash + '.json');
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
    const statsPath = projectStatsPath();
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
      const goal = n.goal ? ` Picking up: ${n.goal}` : '';
      vscode.window.showInformationMessage(`Askr: Context saved — switching chats, no context lost.${goal}`);
      const termOpts = { name: 'askr — new session' };
      if (n.project_path) termOpts.cwd = n.project_path;
      const terminal = vscode.window.createTerminal(termOpts);
      terminal.show();
      const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
        ? ` --allowedTools ${n.allowed_tools.join(',')}`
        : '';
      const launchPrompt = (n.prompt || 'Read the handover and start on the Next Action immediately. Work autonomously.').replace(/"/g, '').replace(/`/g, '');
      terminal.sendText(`claude${toolsFlag}`);
      setTimeout(() => { terminal.sendText(launchPrompt, false); terminal.sendText('\r', false); }, 4000);
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
      setTimeout(() => { terminal.sendText(launchPrompt, false); terminal.sendText('\r', false); }, 4000);
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
        const terminal = vscode.window.createTerminal({ name: 'askr — goal review' });
        terminal.show();
        if (action === 'Mark Done') {
          goals.forEach(g => terminal.sendText(`askr goal done "${g}"`));
        } else if (action === 'Discard') {
          goals.forEach(g => terminal.sendText(`askr goal discard "${g}"`));
        }
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
        const termOpts = { name: 'askr', ...(n.project_path ? { cwd: n.project_path } : {}) };
        const terminal = vscode.window.createTerminal(termOpts);
        terminal.show();
        if (action === 'Add to Goals') {
          const safeDir = (n.direction || preview).replace(/"/g, '').replace(/`/g, '').slice(0, 120);
          terminal.sendText(`askr goal add "${safeDir}"`);
        } else {
          // Start Now — open Claude with this direction as the launch prompt
          const toolsFlag = (n.allowed_tools && n.allowed_tools.length)
            ? ` --allowedTools ${n.allowed_tools.join(',')}`
            : '';
          const safePrompt = (n.prompt || n.direction || '').replace(/"/g, '').replace(/`/g, '');
          terminal.sendText(`claude${toolsFlag}`);
          setTimeout(() => { terminal.sendText(safePrompt, false); terminal.sendText('\r', false); }, 4000);
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
        setTimeout(() => { terminal.sendText(safeInput, false); terminal.sendText('\r', false); }, 4000);
      });
    } else {
      // Quota exhausted — daemon will auto-resume after reset, just inform
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
    const hash = projectHashPrefix();
    if (!fs.existsSync(STATS_DIR)) fs.mkdirSync(STATS_DIR, { recursive: true });
    const watcher = fs.watch(STATS_DIR, (_, filename) => {
      // Trigger on the legacy file OR any per-session file for this project
      if (filename && (filename === hash + '.json' || filename.startsWith(hash + '_'))) {
        refresh();
      }
    });
    context.subscriptions.push({ dispose: () => watcher.close() });
  } catch {}
}

function deactivate() {}

module.exports = { activate, deactivate };
