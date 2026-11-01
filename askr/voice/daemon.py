"""
Voice in the background: `askr voice --daemon`, started by the askr IDE
extension so nobody has to run a command or keep a window open.

One daemon per machine (flock). It talks to whichever Claude Code terminal
was focused last — the extension writes that terminal's shell PID to
voice_focus.json, and a session whose claude process descends from that
shell is the target. With no Claude terminal focused it falls back to the
most recently active live session.

What it's doing — listening, mic level, the live partial transcript, the
last thing it heard and whether it ignored it — goes to voice_status.json,
which the extension shows in the status bar. Every heard line also goes to
voice_heard.jsonl, so a missed wake word can be diagnosed from what Whisper
actually wrote.
"""

import fcntl
import glob
import json
import os
import signal
import subprocess
import sys
import time

from askr.voice import terminal

_DIR = os.path.expanduser("~/.config/askr")
STATUS_PATH = os.path.join(_DIR, "voice_status.json")
FOCUS_PATH = os.path.join(_DIR, "voice_focus.json")
LOCK_PATH = os.path.join(_DIR, "voice_daemon.lock")
PID_PATH = os.path.join(_DIR, "voice_daemon.pid")
LOG_PATH = os.path.join(_DIR, "voice_daemon.log")
HEARD_PATH = os.path.join(_DIR, "voice_heard.jsonl")
DISABLED_PATH = os.path.join(_DIR, "voice_disabled")
PTT_PATH = os.path.join(_DIR, "voice_ptt.json")
# A push-to-talk left on (window closed mid-recording) mustn't record forever.
PTT_MAX_SECS = 120.0
_HEARD_MAX_BYTES = 512 * 1024
CLIPS_DIR = os.path.join(_DIR, "voice_clips")
_CLIPS_KEEP = 40
_STATUS_EVERY_SECS = 0.25


def _write_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp.{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, path)


class StatusFile:
    """Display for the daemon: same interface as ui.Display, but the 'screen'
    is voice_status.json (shown by the extension) plus the heard log."""

    def __init__(self, path: str = STATUS_PATH, clock=time.time):
        self.path = path
        self.clock = clock
        self.state = "starting"
        self.level = self.threshold = 0.0
        self.partial = ""
        self.last = None
        self.session = ""
        self.wake = ""
        self._written = float("-inf")

    def line(self, kind: str, text: str):
        now = self.clock()
        if kind in ("you", "ignored", "notes"):
            heard = text.strip()
            if kind == "ignored" and heard.startswith("heard:"):
                heard = heard[len("heard:"):].split("←")[0].strip()
            _append_heard({"ts": now, "text": heard, "accepted": kind == "you",
                           **({"dictation": True} if kind == "notes" else {})})
        if kind != "info" or text.startswith("talking to"):
            self.last = {"kind": kind, "text": text.strip(), "ts": now}
        if text.startswith("talking to session"):
            self.session = text[len("talking to session"):].strip()
        self._write(force=True)

    def save_clip(self, audio, text: str):
        """Keep the last _CLIPS_KEEP utterances' audio, so a missed wake word
        can be replayed through other Whisper settings on the user's real voice."""
        try:
            import numpy as np
            os.makedirs(CLIPS_DIR, exist_ok=True)
            stem = os.path.join(CLIPS_DIR, f"{self.clock():.2f}")
            np.save(stem + ".npy", np.asarray(audio, dtype=np.float32))
            with open(stem + ".txt", "w") as f:
                f.write(text)
            clips = sorted(f for f in os.listdir(CLIPS_DIR) if f.endswith(".npy"))
            for old in clips[:-_CLIPS_KEEP]:
                for ext in (".npy", ".txt"):
                    try:
                        os.remove(os.path.join(CLIPS_DIR, old[:-4] + ext))
                    except OSError:
                        pass
        except Exception:
            pass

    def status(self, state: str, level: float = 0.0, threshold: float = 0.0, partial: str = ""):
        self.state, self.level, self.threshold, self.partial = state, level, threshold, partial
        self._write()

    def _write(self, force: bool = False):
        now = self.clock()
        if not force and now - self._written < _STATUS_EVERY_SECS:
            return
        self._written = now
        try:
            _write_json(self.path, {
                "pid": os.getpid(), "ts": now, "state": self.state,
                "level": round(self.level, 5), "threshold": round(self.threshold, 5),
                "partial": self.partial, "last": self.last, "session": self.session,
                "wake": self.wake, "notes": _notes_title(),
            })
        except OSError:
            pass


def _notes_title() -> str:
    from askr.voice import notes
    state = notes.active()
    return state["title"] if state else ""


def _append_heard(entry: dict):
    try:
        if os.path.exists(HEARD_PATH) and os.path.getsize(HEARD_PATH) > _HEARD_MAX_BYTES:
            os.replace(HEARD_PATH, HEARD_PATH + ".1")
        with open(HEARD_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def ptt_on(now: float | None = None) -> bool:
    """Push-to-talk is held: the IDE shortcut toggled it on (voice_ptt.json)."""
    try:
        with open(PTT_PATH) as f:
            state = json.load(f)
    except (OSError, ValueError):
        return False
    now = time.time() if now is None else now
    return bool(state.get("on")) and now - float(state.get("ts") or 0) < PTT_MAX_SECS


# --- which session -------------------------------------------------------

_ancestor_cache: dict = {}


def _ancestors(pid: int) -> list:
    if pid not in _ancestor_cache:
        from askr.session.lifecycle import _get_ancestor_pids
        _ancestor_cache[pid] = [pid] + _get_ancestor_pids(pid)
    return _ancestor_cache[pid]


def live_sessions() -> dict:
    """session_id -> claude pid, for sessions whose claude is still running."""
    out = {}
    try:
        names = os.listdir(terminal._PIDS_DIR)
    except OSError:
        return out
    for sid in names:
        pid = terminal.session_pid(sid)
        if pid:
            out[sid] = pid
    return out


def transcript_for(session_id: str) -> str:
    hits = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{session_id}.jsonl"))
    return max(hits, key=os.path.getmtime) if hits else ""


def focused_shell_pid() -> int | None:
    try:
        with open(FOCUS_PATH) as f:
            return int(json.load(f).get("shell_pid") or 0) or None
    except (OSError, ValueError, TypeError):
        return None


def target_transcript() -> str:
    """Transcript of the focused Claude terminal's session, else the most recently active live one."""
    sessions = live_sessions()
    shell = focused_shell_pid()
    if shell:
        for sid, pid in sessions.items():
            if shell in _ancestors(pid):
                path = transcript_for(sid)
                if path:
                    return path
    paths = [p for p in (transcript_for(sid) for sid in sessions) if p]
    return max(paths, key=os.path.getmtime) if paths else ""


# --- lifecycle -----------------------------------------------------------

def running_pid() -> int | None:
    try:
        with open(PID_PATH) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        return None


def acquire_lock():
    """The lock file handle (keep it open for the daemon's lifetime), or None if another daemon holds it."""
    os.makedirs(_DIR, exist_ok=True)
    fh = open(LOCK_PATH, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        fh.close()
        return None
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    return fh


def start_detached() -> bool:
    """Spawn the daemon in the background unless one is running or voice is turned off."""
    if os.path.exists(DISABLED_PATH) or running_pid():
        return False
    os.makedirs(_DIR, exist_ok=True)
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env = dict(os.environ, PYTHONPATH=repo)
    log = open(LOG_PATH, "a")
    subprocess.Popen([sys.executable, "-m", "askr.cli.askr", "voice", "--daemon"],
                     cwd=os.path.expanduser("~"), env=env, stdout=log,
                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    return True


def stop() -> bool:
    pid = running_pid()
    if not pid:
        return False
    try:
        os.kill(pid, signal.SIGINT)
    except OSError:
        return False
    return True


def set_enabled(enabled: bool):
    if enabled:
        try:
            os.remove(DISABLED_PATH)
        except OSError:
            pass
    else:
        os.makedirs(_DIR, exist_ok=True)
        open(DISABLED_PATH, "w").close()
