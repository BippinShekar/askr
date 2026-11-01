"""
Errands asked for by voice that have nothing to do with the open Claude Code
session — "open a random YouTube video", "look up X", "draft a reply to Y".
Typing those into the session (what happened before 2026-11-01) derails
whatever it's working on and clutters its transcript, so they run in a
separate, hidden headless Claude (`claude -p`, same "auto" permission mode
the user runs in) and the result is spoken back.

Each run gets its own folder under voice_tasks/ (no askr_state there, so
askr's hooks stay quiet) holding the prompt and the full output.
"""

import json
import os
import queue
import subprocess
import threading
import time
from dataclasses import dataclass

TASKS_DIR = os.path.expanduser("~/.config/askr/voice_tasks")
TIMEOUT_SECS = 30 * 60
_SYSTEM = ("You are running a background errand the user asked for by voice, away from their main "
           "coding session. Do it end to end without asking questions — make reasonable choices. "
           "Finish with one or two plain sentences saying what you did or found; they are read aloud.")


@dataclass
class Done:
    task: str
    result: str
    ok: bool
    folder: str


class Tasks:
    def __init__(self, runner=None):
        self.finished: queue.Queue = queue.Queue()
        self._runner = runner or _run_claude
        self._lock = threading.Lock()
        self.running: list = []

    def start(self, task: str) -> str:
        folder = os.path.join(TASKS_DIR, time.strftime("%Y%m%d-%H%M%S"))
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "task.txt"), "w") as f:
            f.write(task)
        with self._lock:
            self.running.append(task)
        threading.Thread(target=self._run, args=(task, folder), daemon=True).start()
        return folder

    def _run(self, task: str, folder: str):
        try:
            ok, result = self._runner(task, folder)
        except Exception as e:
            ok, result = False, f"It failed: {e}"
        with open(os.path.join(folder, "result.txt"), "w") as f:
            f.write(result)
        with self._lock:
            if task in self.running:
                self.running.remove(task)
        self.finished.put(Done(task, result, ok, folder))


def claude_env() -> dict:
    """Environment for the hidden Claude: the user's Claude login, never an API key.
    Found 2026-11-02: askr's CLI loads ANTHROPIC_API_KEY from its .env, the
    daemon inherited it, and claude -p — which prefers an API key over the
    claude.ai login — failed every task with "Credit balance is too low"."""
    env = dict(os.environ)
    for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
        env.pop(key, None)
    return env


def _run_claude(task: str, folder: str) -> tuple:
    proc = subprocess.run(
        ["claude", "-p", "--permission-mode", "auto", "--output-format", "json",
         "--append-system-prompt", _SYSTEM, task],
        cwd=folder, env=claude_env(), capture_output=True, text=True, timeout=TIMEOUT_SECS,
        stdin=subprocess.DEVNULL)
    with open(os.path.join(folder, "output.json"), "w") as f:
        f.write(proc.stdout)
    if proc.stderr:
        with open(os.path.join(folder, "stderr.txt"), "w") as f:
            f.write(proc.stderr)
    try:
        data = json.loads(proc.stdout)
        return (not data.get("is_error") and proc.returncode == 0), str(data.get("result") or "").strip()
    except ValueError:
        return False, (proc.stderr or proc.stdout or "no output").strip()[-500:]
