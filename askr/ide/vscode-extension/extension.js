const vscode = require('vscode');
const fs = require('fs');
const path = require('path');
const os = require('os');

const STATS_PATH = path.join(os.homedir(), '.config', 'askr', 'session_stats.json');
const POLL_MS = 5000;

const COLOR_OK   = '#98c379';  // green  — < 50%
const COLOR_WARN = '#e5c07b';  // amber  — 50–75%
const COLOR_HIGH = '#e06c75';  // red    — 75–90%
const COLOR_CRIT = '#ff5555';  // bright red — ≥ 90%
const COLOR_IDLE = '#6b7280';  // grey   — stale session

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

function timeAgo(ms) {
  const s = Math.floor(ms / 1000);
  if (s < 60)  return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60)  return `${m}m ago`;
  return `${Math.floor(m / 60)}h ago`;
}

function buildTooltip(s, ctxPct, resetInfo, staleMs) {
  const ctxTokens  = (s.context_tokens || 0).toLocaleString();
  const ctxWindow  = (s.context_window || 200000).toLocaleString();
  const ctxLabel   = s.context_label || 'ok';
  const turns      = s.turns || 0;
  const model      = s.model || 'claude';
  const sessionId  = s.session_id ? s.session_id.slice(0, 8) + '…' : '?';

  const isLive = staleMs < 120_000;
  const freshnessLine = isLive
    ? `🟢 **Live** — last updated just now`
    : `🟡 **Last active chat** (updated ${timeAgo(staleMs)}) — no active Claude Code session`;

  const labelMessages = {
    'checkpoint':  '\n\n⚠ **Checkpoint imminent** — askr will save state and start a new chat.',
    'near limit':  '\n\n🔴 **Near limit** — approaching 90%. Askr will checkpoint soon.',
    'high':        '\n\n🟡 **High** — past 75%. Monitor usage.',
  };
  const ctxEtaLine = labelMessages[ctxLabel] || '';

  let resetLine = '';
  if (resetInfo) {
    resetLine = `\n\n---\n\n**↺ resets ${resetInfo.text.replace('↺', '')}** — 5-hour Anthropic quota window\n\n`
      + `Not per-chat — this is the rolling usage window across all chats.\n`
      + `After reset, your quota refreshes. Check **claude.ai → Settings → Usage** for your actual %.`;
  }

  const md = new vscode.MarkdownString(
    `**Askr** — Claude Code session tracker\n\n`
    + `${freshnessLine}\n\n`
    + `---\n\n`
    + `**${ctxPct}% — this chat's context window**\n\n`
    + `${ctxTokens} / ${ctxWindow} tokens in the **current conversation** (${model}).\n\n`
    + `Each chat has its own 200k token window. This counter resets when you open a **new chat**, `
    + `not when the quota resets. At 90%, askr checkpoints state and starts a new chat automatically.`
    + ctxEtaLine
    + `\n\n${turns} turns · session \`${sessionId}\``
    + resetLine
    + `\n\n---\n*Click to run \`askr status\` in terminal*`
  );
  md.isTrusted = true;
  return md;
}

function readStats() {
  try {
    const raw  = fs.readFileSync(STATS_PATH, 'utf8');
    const s    = JSON.parse(raw);
    const mtime = fs.statSync(STATS_PATH).mtimeMs;
    const staleMs = Date.now() - mtime;

    // Hide entirely if last update was more than 2 hours ago
    if (staleMs > 7_200_000) return null;

    const ctxPct    = Math.round((s.context_pct || 0) * 100);
    const ctxLabel  = s.context_label || 'ok';
    const resetInfo = s.reset_at ? resetCountdown(s.reset_at) : null;
    const resetStr  = resetInfo ? ` ${resetInfo.text}` : '';
    const isLive    = staleMs < 120_000;

    const labelSuffix = { 'checkpoint': ' ⚠', 'near limit': ' !', 'high': '' };
    let label = `askr ${ctxPct}%${resetStr}${labelSuffix[ctxLabel] || ''}`;
    if (!isLive) label += ' …';  // trailing … signals no active session

    const color = isLive ? ctxColor(ctxPct) : COLOR_IDLE;

    return {
      label,
      color,
      tooltip: buildTooltip(s, ctxPct, resetInfo, staleMs),
    };
  } catch {
    return null;
  }
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
    const statsDir = path.dirname(STATS_PATH);
    if (fs.existsSync(statsDir)) {
      const watcher = fs.watch(statsDir, (_, filename) => {
        if (filename === 'session_stats.json') refresh();
      });
      context.subscriptions.push({ dispose: () => watcher.close() });
    }
  } catch { /* polling fallback */ }
}

function deactivate() {}

module.exports = { activate, deactivate };
