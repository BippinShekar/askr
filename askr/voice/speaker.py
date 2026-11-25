"""
Spoken output for voice mode. Separate from clients.voice.speak(): voice
mode is something the user explicitly started, so it isn't gated on the
voice_notifications preference, and replies run longer than a notification.
Shares the same cross-process lock so it never talks over a daemon
announcement. Mutes the mic for the duration so askr never hears itself.
"""

import os
import shutil
import subprocess
import time

from askr.clients import voice as _voice
from askr.clients.voice import _acquire_voice_lock, _release_voice_lock, humanize_for_speech

_ECHO_TAIL_SECS = 0.4  # room reverb after `say` exits
_CUE_SOUND = "/System/Library/Sounds/Tink.aiff"


class Speaker:
    def __init__(self, listener=None, gate=None, voice: str = "", rate: int = 0):
        self.listener = listener
        self.gate = gate
        self.voice = voice  # overrides askr's one voice (clients.voice.say_command) only if set
        self.rate = rate
        self.say_bin = shutil.which("say")
        self._proc = None

    def cue(self):
        """Non-blocking tick: askr heard you. Silent while muted."""
        if _voice.is_muted() or not os.path.exists(_CUE_SOUND):
            return
        try:
            subprocess.Popen(["afplay", "-v", "0.4", _CUE_SOUND],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def stop(self):
        """Cut off whatever is being said right now (⌘M mid-sentence)."""
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()

    def speak(self, text: str):
        text = humanize_for_speech(text or "", max_len=600)
        if not text or not self.say_bin or _voice.is_muted():
            return
        cmd = _voice.say_command(self.say_bin, text)
        if self.voice:
            cmd[1:1] = ["-v", self.voice] if "-v" not in cmd else []
            if "-v" in cmd:
                cmd[cmd.index("-v") + 1] = self.voice
        if self.rate:
            cmd[cmd.index("-r") + 1] = str(self.rate)
        if self.listener:
            self.listener.muted.set()
        lock_fd = _acquire_voice_lock()
        try:
            if not _voice.is_muted():  # may have been muted while waiting for the lock
                self._proc = subprocess.Popen(cmd)
                self._proc.wait(timeout=90)
        except Exception:
            if self._proc and self._proc.poll() is None:
                self._proc.kill()
        finally:
            self._proc = None
            _release_voice_lock(lock_fd)
            time.sleep(_ECHO_TAIL_SECS)
            if self.listener:
                self.listener.muted.clear()
            if self.gate:
                self.gate.open_window(time.time())
