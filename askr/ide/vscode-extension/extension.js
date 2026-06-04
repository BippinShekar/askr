const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');

const STATS_PATH = path.join(os.homedir(), '.config', 'askr', 'session_stats.json');
const POLL_MS = 5000;

function resetCountdown(resetAtIso) {
  try {
    const reset = new Date(resetAtIso);
    const remainMs = reset - Date.now();
    if (remainMs <= 0) return '↺now';
    const h = Math.floor(remainMs / 3600000);
    const m = Math.floor((remainMs % 3600000) / 60000);
    return h > 0 ? `↺${h}h${String(m).padStart(2, '0')}m` : `↺${m}m`;
  } catch {
    return '';
  }
}

function readStats() {
  try {
    const raw = fs.readFileSync(STATS_PATH, 'utf8');
    const s = JSON.parse(raw);

    const mtime = fs.statSync(STATS_PATH).mtimeMs;
    // stale if not updated in 10 minutes — session probably idle or ended
    if (Date.now() - mtime > 600_000) return null;

    const ctxPct = Math.round((s.context_pct || 0) * 100);
    const ctxEta = s.context_eta_turns;
    const resetAt = s.reset_at || '';
    const resetStr = resetAt ? ' ' + resetCountdown(resetAt) : '';

    let suffix = '';
    if (ctxPct >= 90) suffix = ' ⚠';
    else if (ctxEta && ctxEta < 20) suffix = ` (${ctxEta}t)`;

    return `askr ${ctxPct}%${resetStr}${suffix}`;
  } catch {
    return null;
  }
}

function activate(context) {
  const item = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    1000
  );
  item.tooltip = 'Askr — Claude Code context usage. Click for details.';
  item.command = 'askr.openStatus';

  context.subscriptions.push(
    vscode.commands.registerCommand('askr.openStatus', () => {
      const terminal = vscode.window.createTerminal('askr status');
      terminal.show();
      terminal.sendText('askr status');
    })
  );

  function refresh() {
    const text = readStats();
    if (text) {
      item.text = text;
      item.show();
    } else {
      item.hide();
    }
  }

  refresh();
  const timer = setInterval(refresh, POLL_MS);

  context.subscriptions.push(item);
  context.subscriptions.push({ dispose: () => clearInterval(timer) });

  // also refresh on file change if possible
  try {
    const statsDir = path.dirname(STATS_PATH);
    if (fs.existsSync(statsDir)) {
      const watcher = fs.watch(statsDir, (_, filename) => {
        if (filename === 'session_stats.json') refresh();
      });
      context.subscriptions.push({ dispose: () => watcher.close() });
    }
  } catch {
    // fs.watch unavailable — polling fallback is fine
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
