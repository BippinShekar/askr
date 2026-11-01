// Loader for the askr extension (the real code is main.js).
//
// Cursor only loads an extension's code at window start, so every askr
// update used to need "Developer: Reload Window" — found 2026-11-01: the
// voice status bar kept saying `say "askr …"` long after the wake word was
// changed, because the window still ran the old code. This watches main.js
// and swaps it in place when `askr` installs a new one: the new module is
// loaded first (a half-copied file keeps the old one running), then the old
// one's commands, timers and status bar items are disposed and the new one
// activated. Changes to package.json (keybindings, command titles) still
// need a window reload.
const fs = require('fs');
const path = require('path');

const MAIN = path.join(__dirname, 'main.js');
const CHECK_MS = 3000;

let current = null;  // { mod, subscriptions, mtime }

function dispose(entry) {
  if (!entry) return;
  try { if (entry.mod.deactivate) entry.mod.deactivate(); } catch {}
  for (const d of entry.subscriptions) {
    try { d.dispose(); } catch {}
  }
}

function load(context) {
  const mtime = fs.statSync(MAIN).mtimeMs;
  delete require.cache[require.resolve(MAIN)];
  let mod;
  try {
    mod = require(MAIN);
  } catch (e) {
    console.error(`Askr: main.js failed to load, keeping the running version: ${e && e.stack || e}`);
    if (current) current.mtime = mtime;  // don't retry the same broken file every tick
    return;
  }
  dispose(current);
  const sub = { subscriptions: [], extensionPath: context.extensionPath,
                globalState: context.globalState, workspaceState: context.workspaceState };
  current = { mod, subscriptions: sub.subscriptions, mtime };
  try {
    mod.activate(sub);
  } catch (e) {
    console.error(`Askr: main.js activate threw: ${e && e.stack || e}`);
  }
}

function activate(context) {
  load(context);
  const timer = setInterval(() => {
    try {
      if (current && fs.statSync(MAIN).mtimeMs !== current.mtime) {
        console.log('Askr: main.js changed — reloading in place');
        load(context);
      }
    } catch (e) {
      console.error(`Askr: reload check failed: ${e}`);
    }
  }, CHECK_MS);
  context.subscriptions.push({ dispose: () => { clearInterval(timer); dispose(current); current = null; } });
}

function deactivate() {}

module.exports = { activate, deactivate };
