"""
Controlling the Mac by voice: the actions behind the voice agent's Mac tools.

Everyday actions (apps, volume, media, opening files, clipboard, a
notification) run directly — they're quick and easy to undo. Shell commands
and arbitrary AppleScript can do anything, so they're never run on the
first ask: `prepare_risky` returns a spoken summary, and they only run when
the user says yes (askr/voice/loop.py confirm flow). A short blocklist is
refused outright, confirmed or not.
"""

import os
import re
import shlex
import subprocess

_TIMEOUT = 20


def _osa(script: str) -> tuple:
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=_TIMEOUT)
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def _q(s: str) -> str:
    """AppleScript string literal."""
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


# --- everyday actions ------------------------------------------------------

def open_app(name: str) -> str:
    r = subprocess.run(["open", "-a", name], capture_output=True, text=True, timeout=_TIMEOUT)
    return f"opened {name}" if r.returncode == 0 else f"error: couldn't open {name!r} — {r.stderr.strip()[:120]}"


def quit_app(name: str) -> str:
    ok, out = _osa(f"tell application {_q(name)} to quit")
    return f"quit {name}" if ok else f"error: couldn't quit {name!r} — {out[:120]}"


def running_apps() -> str:
    ok, out = _osa('tell application "System Events" to get name of every application process '
                   'whose background only is false')
    return out if ok else f"error: {out[:160]}"


def set_volume(level: int | None = None, mute: bool | None = None) -> str:
    if mute is not None:
        ok, out = _osa(f"set volume output muted {'true' if mute else 'false'}")
        return ("muted" if mute else "unmuted") if ok else f"error: {out}"
    level = max(0, min(int(level or 0), 100))
    ok, out = _osa(f"set volume output volume {level}")
    return f"volume {level}%" if ok else f"error: {out}"


def get_volume() -> str:
    ok, out = _osa("output volume of (get volume settings)")
    return f"volume {out}%" if ok else f"error: {out}"


_MEDIA = {"play": "play", "pause": "pause", "toggle": "playpause", "next": "next track",
          "previous": "previous track"}


def media(action: str, app: str = "") -> str:
    """Play/pause/skip in Spotify or Music — whichever is running, or `app`."""
    verb = _MEDIA.get(action)
    if not verb:
        return f"error: unknown media action {action!r}"
    candidates = [app] if app else ["Spotify", "Music"]
    for name in candidates:
        ok, running = _osa(f'application {_q(name)} is running')
        if ok and running == "true":
            ok, out = _osa(f"tell application {_q(name)} to {verb}")
            return f"{action} in {name}" if ok else f"error: {out[:120]}"
    return "error: neither Spotify nor Music is running"


def open_path(path: str, reveal: bool = False) -> str:
    path = os.path.expanduser(path)
    if not os.path.exists(path):
        return f"error: {path} doesn't exist"
    r = subprocess.run(["open"] + (["-R"] if reveal else []) + [path], capture_output=True, text=True,
                       timeout=_TIMEOUT)
    return ("revealed " if reveal else "opened ") + path if r.returncode == 0 else f"error: {r.stderr.strip()}"


def find_files(query: str, limit: int = 8) -> str:
    """Spotlight search by name, under the home folder."""
    r = subprocess.run(["mdfind", "-onlyin", os.path.expanduser("~"), "-name", query],
                       capture_output=True, text=True, timeout=_TIMEOUT)
    noise = ("/Library/", "/.", "/node_modules/", "/venv/", "/__pycache__/", "/build/", "/dist/")
    hits = [h for h in r.stdout.splitlines() if not any(n in h for n in noise)][:limit]
    return "\n".join(hits) if hits else f"nothing named like {query!r}"


def clipboard(text: str | None = None) -> str:
    if text is None:
        out = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=_TIMEOUT).stdout
        return out[:2000] if out else "(clipboard is empty)"
    subprocess.run(["pbcopy"], input=text, text=True, timeout=_TIMEOUT)
    return "copied to the clipboard"


def notify(title: str, message: str = "") -> str:
    ok, out = _osa(f"display notification {_q(message)} with title {_q(title)}")
    return "notification shown" if ok else f"error: {out}"


# --- risky actions: confirmed out loud first ---------------------------------

# Refused even when confirmed: too destructive to trust a misheard "yes".
_BLOCKED = [
    r"\bsudo\b", r"\brm\s+(-\w*\s+)*-\w*[rf]\w*\s+(/|~|\$HOME)(\s|$)", r"\bdiskutil\s+(erase|partition)",
    r"\bmkfs\b", r"\bdd\s+.*of=/dev/", r":\(\)\s*\{", r"\bshutdown\b", r"\breboot\b", r"\bhalt\b",
    r"\bcsrutil\b", r"\bnvram\b", r"\blaunchctl\s+(unload|remove)\b.*system",
]


def blocked(command: str) -> str:
    for pat in _BLOCKED:
        if re.search(pat, command):
            return f"refused: `{command[:80]}` is on askr's never-run list"
    return ""


def prepare_risky(kind: str, code: str) -> tuple:
    """(spoken summary, error) for a shell command or AppleScript about to need a yes."""
    code = (code or "").strip()
    if not code:
        return "", "error: nothing to run"
    if kind == "shell":
        why = blocked(code)
        if why:
            return "", f"error: {why}"
        first = shlex.split(code)[0] if code else ""
        return f"run {os.path.basename(first)} in the terminal", ""
    return "run an AppleScript", ""


def run_risky(kind: str, code: str, cwd: str = "") -> str:
    if kind == "shell":
        why = blocked(code)
        if why:
            return f"error: {why}"
        r = subprocess.run(["/bin/zsh", "-lc", code], capture_output=True, text=True, timeout=120,
                           cwd=os.path.expanduser(cwd) if cwd else os.path.expanduser("~"))
        out = (r.stdout + ("\n" + r.stderr if r.stderr else "")).strip()
        return (f"exit {r.returncode}: " if r.returncode else "") + (out[-1500:] or "done, no output")
    ok, out = _osa(code)
    return out[-1500:] if ok else f"error: {out[-300:]}"
