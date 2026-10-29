"""
Spoken output for voice mode. Separate from clients.voice.speak(): voice
mode is something the user explicitly started, so it isn't gated on the
voice_notifications preference, and replies run longer than a notification.
Shares the same cross-process lock so it never talks over a daemon
announcement. Mutes the mic for the duration so askr never hears itself.
"""

import shutil
import subprocess
import time

from askr.clients.voice import _acquire_voice_lock, _release_voice_lock, humanize_for_speech

_ECHO_TAIL_SECS = 0.4  # room reverb after `say` exits


class Speaker:
    def __init__(self, listener=None, gate=None, voice: str = "", rate: int = 0):
        self.listener = listener
        self.gate = gate
        self.voice = voice
        self.rate = rate
        self.say_bin = shutil.which("say")

    def speak(self, text: str):
        text = humanize_for_speech(text or "", max_len=600)
        if not text or not self.say_bin:
            return
        cmd = [self.say_bin]
        if self.voice:
            cmd += ["-v", self.voice]
        if self.rate:
            cmd += ["-r", str(self.rate)]
        cmd.append(text)
        if self.listener:
            self.listener.muted.set()
        lock_fd = _acquire_voice_lock()
        try:
            subprocess.run(cmd, timeout=90, check=False)
        except Exception:
            pass
        finally:
            _release_voice_lock(lock_fd)
            time.sleep(_ECHO_TAIL_SECS)
            if self.listener:
                self.listener.muted.clear()
            if self.gate:
                self.gate.open_window(time.time())
