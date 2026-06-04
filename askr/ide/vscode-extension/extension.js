const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');

const STATS_PATH = path.join(os.homedir(), '.config', 'askr', 'session_stats.json');
const POLL_MS = 5000;

// Color thresholds for context %
const COLOR_OK      = '#98c379';  // green  — < 50%
const COLOR_WARN    = '#e5c07b';  // amber  — 50–75%
const COLOR_HIGH    = '#e06c75';  // red    — 75–90%
const COLOR_CRIT    = '#ff5555';  // bright red — ≥ 90%

function ctxColor(pct) {
  if (pct >= 90) return COLOR_CRIT;
  if (pct >= 75) return COLOR_HIGH;
  if (pct >= 50) return COLOR_WARN;
  return COLOR_OK;
}

function resetCountdown(resetAtIso) {
  try {
    const reset = new Date(resetAtIso);
    const remainMs = reset - Date.now();
    if (remainMs <= 0) return { text: '↺now', h: 0, m: 0 };
    const h = Math.floor(remainMs / 3600000);
    const m = Math.floor((remainMs % 3600000) / 60000);
    return { text: h > 0 ? `↺${h}h${String(m).padStart(2, '0')}m` : `↺${m}m`, h, m };
  } catch {
    return null;
  }
}

function buildTooltip(s, ctxPct, resetInfo) {
  const ctxTokens = (s.context_tokens || 0).toLocaleString();
  const ctxWindow = (s.context_window || 200000).toLocaleString();
  const ctxEta = s.context_eta_turns;
  const turns = s.turns || 0;
  const model = s.model || 'claude';

  let ctxStatus = '';
  if (ctxPct >= 90) ctxStatus = '⚠ **checkpoint imminent**';
  else if (ctxEta && ctxEta < 20) ctxStatus = `⚠ ~${ctxEta} turns until checkpoint`;
  else if (ctxEta) ctxStatus = `~${ctxEta} turns remaining`;

  let resetLine = '';
  if (resetInfo) {
    resetLine = `\n\n**↺ ${resetInfo.text.replace('↺', '')}** — quota window resets\n`
      + `This is your 5-hour Anthropic usage window. After reset, your quota refreshes.\n`
      + `Check **claude.ai → Settings → Usage** for your exact % used.`;
  }

  const md = new vscode.MarkdownString(
    `**Askr** — Claude Code session tracker\n\n`
    + `---\n\n`
    + `**${ctxPct}% context** — *this chat only*\n\n`
    + `${ctxTokens} / ${ctxWindow} tokens used in the current conversation (${model}).\n`
    + `This resets when you start a **new chat**. At 90%, askr checkpoints and opens a fresh chat so nothing is lost.\n`
    + (ctxStatus ? `\n${ctxStatus}\n` : '')
    + `\n${turns} turns so far.`
    + resetLine
    + `\n\n---\n*Click to run \`askr status\` in terminal*`
  );
  md.isTrusted = true;
  return md;
}

function readStats() {
  try {
    const raw = fs.readFileSync(STATS_PATH, 'utf8');
    const s = JSON.parse(raw);

    const mtime = fs.statSync(STATS_PATH).mtimeMs;
    if (Date.now() - mtime > 600_000) return null;  // stale — session idle/ended

    const ctxPct = Math.round((s.context_pct || 0) * 100);
    const ctxEta = s.context_eta_turns;
    const resetInfo = s.reset_at ? resetCountdown(s.reset_at) : null;
    const resetStr = resetInfo ? ` ${resetInfo.text}` : '';

    let label = `askr ${ctxPct}%${resetStr}`;
    if (ctxPct >= 90) label += ' ⚠';
    else if (ctxEta && ctxEta < 20) label += ` (${ctxEta}t)`;

    return { label, color: ctxColor(ctxPct), tooltip: buildTooltip(s, ctxPct, resetInfo) };
  } catch {
    return null;
  }
}

function activate(context) {
  const item = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    1000
  );
  item.command = 'askr.openStatus';

  context.subscriptions.push(
    vscode.commands.registerCommand('askr.openStatus', () => {
      const terminal = vscode.window.createTerminal({ name: 'askr' });
      terminal.show();
      terminal.sendText('askr status');
    })
  );

  function refresh() {
    const result = readStats();
    if (result) {
      item.text = result.label;
      item.color = result.color;
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
    const statsDir = path.dirname(STATS_PATH);
    if (fs.existsSync(statsDir)) {
      const watcher = fs.watch(statsDir, (_, filename) => {
        if (filename === 'session_stats.json') refresh();
      });
      context.subscriptions.push({ dispose: () => watcher.close() });
    }
  } catch {
    // fs.watch unavailable — polling is the fallback
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
