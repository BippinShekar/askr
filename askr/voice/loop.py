"""
`askr voice` — talk to the Claude Code session running in this project.

  mic -> Segmenter -> Whisper -> WakeGate -> Talker ─┬─ say  -> Speaker
                                                     └─ send -> terminal (or Stop-hook inbox)
  session transcript -> Narrator -> Talker.narrate -> Speaker

Runs in its own Terminal.app window (see launch_window) so there's one
obvious place showing that it's listening, the mic level, and everything it
hears — including lines it ignored and why.
"""

import os
import platform
import queue
import shlex
import shutil
import subprocess
import sys
import time

from askr.voice import inbox, session, terminal
from askr.voice.narrator import Narrator
from askr.voice.wake import WakeGate

_RETARGET_EVERY_SECS = 10.0
_CLAIM_TIMEOUT_SECS = 6.0
_PARTIAL_EVERY_SECS = 1.0
_WINDOW_ENV = "ASKR_VOICE_WINDOW"


class _NullDisplay:
    def line(self, kind, text):
        pass

    def status(self, *a, **k):
        pass


class VoiceLoop:
    def __init__(self, project_path: str, listener, transcriber, talker, speaker,
                 session_id: str = "", display=None, clock=time.time):
        self.project_path = project_path
        self.listener = listener
        self.transcriber = transcriber
        self.talker = talker
        self.speaker = speaker
        self.gate = speaker.gate or WakeGate()
        self.pinned_session = session_id
        self.display = display or _NullDisplay()
        self.clock = clock
        self.transcript_path = ""
        self.narrator = None
        self.last_request = ""
        self._last_retarget = 0.0
        self._last_partial = 0.0
        self._partial = ""

    # --- display ---------------------------------------------------------

    def _status(self, state: str, partial: str = ""):
        seg = getattr(self.listener, "segmenter", None)
        level = getattr(seg, "level", 0.0) if seg else 0.0
        threshold = seg._threshold() if seg else 0.0
        self.display.status(state, level, threshold, partial)

    def _speak(self, text: str):
        self._status("speaking")
        self.speaker.speak(text)

    # --- target session --------------------------------------------------

    @property
    def session_id(self) -> str:
        return os.path.basename(self.transcript_path).removesuffix(".jsonl")

    def retarget(self, force: bool = False):
        now = self.clock()
        if not force and now - self._last_retarget < _RETARGET_EVERY_SECS:
            return
        self._last_retarget = now
        if self.pinned_session:
            folder = os.path.dirname(session.find_latest_transcript(self.project_path) or "")
            path = os.path.join(folder, f"{self.pinned_session}.jsonl") if folder else ""
        else:
            path = session.find_latest_transcript(self.project_path) or ""
        if path and path != self.transcript_path:
            self.transcript_path = path
            self.narrator = Narrator(path)
            d = session.digest(path)
            what = f" — last request: {d.last_prompt[:70]}" if d.last_prompt else ""
            self.display.line("info", f"talking to session {self.session_id[:8]}{what}")

    # --- one utterance ---------------------------------------------------

    def handle_utterance(self, audio):
        self._status("transcribing", self._partial)
        self._partial = ""
        text = self.transcriber.transcribe(audio)
        if not text:
            self.display.line("ignored", "  (heard sound, no words)")
            return
        command = self.gate.accept(text, self.clock())
        if command is None:
            self.display.line("ignored", f"  heard: {text}   ← no wake word, ignored")
            return
        self.display.line("you", command)
        if not self.transcript_path:
            self._speak("I can't find a Claude Code session in this project.")
            return
        self._status("thinking")
        d = session.digest(self.transcript_path)
        reply = self.talker.respond(command, d.render())
        self.display.line("askr", reply.say)
        if reply.send:
            self.display.line("claude", f"  → {reply.send}")
        self._speak(reply.say)
        if self.narrator:
            self.narrator.mark_spoken(self.clock())
        if reply.send:
            self.last_request = reply.send
            self._status("sending")
            self.deliver(reply.send, d.in_flight)

    def deliver(self, text: str, in_flight: bool):
        if terminal.type_prompt(self.session_id, text, self.project_path) and self._claimed():
            self.display.line("info", "  delivered to the session's terminal")
            return
        if in_flight:
            inbox.post(self.session_id, text)
            self.display.line("error", "  terminal not found — queued for the end of this turn")
            self._speak("I couldn't reach its terminal, so it'll get that when it finishes this step.")
        else:
            self.display.line("error", "  terminal not found — not delivered")
            self._speak("I couldn't find that session's terminal. Is the askr extension running in Cursor?")

    def _claimed(self) -> bool:
        """The extension deletes voice_prompt.json once it has typed it."""
        deadline = self.clock() + _CLAIM_TIMEOUT_SECS
        while self.clock() < deadline:
            if not os.path.exists(terminal._VOICE_PROMPT_PATH):
                return True
            time.sleep(0.2)
        try:
            os.remove(terminal._VOICE_PROMPT_PATH)  # don't let it fire late, after the fallback
        except OSError:
            pass
        return False

    # --- live partial transcription ---------------------------------------

    def update_partial(self):
        seg = getattr(self.listener, "segmenter", None)
        if not seg or not seg.active:
            return
        now = self.clock()
        if now - self._last_partial < _PARTIAL_EVERY_SECS:
            return
        self._last_partial = now
        audio = seg.snapshot()
        if audio is not None:
            self._partial = self.transcriber.transcribe(audio)

    # --- narration -------------------------------------------------------

    def narrate(self):
        if not self.narrator:
            return
        for event in self.narrator.poll(self.clock()):
            self._status("thinking")
            spoken = self.talker.narrate(event.text, self.last_request) or event.text
            if event.kind == "question":
                spoken = f"It's asking: {spoken}"
            self.display.line("askr", spoken)
            self._speak(spoken)
            self.talker.note_update(spoken)

    # --- main loop -------------------------------------------------------

    def run_once(self, wait: float = 0.15):
        self.retarget()
        try:
            audio = self.listener.utterances.get(timeout=wait)
        except queue.Empty:
            audio = None
        if audio is not None:
            self.handle_utterance(audio)
        else:
            self.update_partial()
        self.narrate()
        seg = getattr(self.listener, "segmenter", None)
        hearing = bool(seg and seg.active)
        self._status("hearing…" if hearing else "listening", self._partial if hearing else "")

    def run(self):
        self.retarget(force=True)
        self.listener.start()
        self.display.line("info", 'listening — start with "askr …"   (Ctrl+C to stop)')
        try:
            while True:
                self.run_once()
        except KeyboardInterrupt:
            self.display.line("info", "stopped")
        finally:
            self.listener.stop()


def launch_window(project: str, args: list) -> bool:
    """Open a Terminal.app window running voice mode; True if launched."""
    if platform.system() != "Darwin":
        return False
    askr_bin = shutil.which("askr") or f"{sys.executable} -m askr.cli.askr"
    cmd = (f"cd {shlex.quote(project)} && {_WINDOW_ENV}=1 {askr_bin} voice "
           + " ".join(shlex.quote(a) for a in args))
    from askr.session.lifecycle import _applescript_quote
    script = f'tell application "Terminal"\n  do script {_applescript_quote(cmd)}\n  activate\nend tell'
    return subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10).returncode == 0


def main(args: list):
    from askr.session.monitor import find_project_root
    project = find_project_root() or os.getcwd()

    if "--here" not in args and not os.environ.get(_WINDOW_ENV):
        if launch_window(project, args):
            print("askr voice opened in a Terminal window — talk to it there.")
            return

    session_id = ""
    if "--session" in args:
        i = args.index("--session")
        session_id = args[i + 1] if i + 1 < len(args) else ""

    from askr.voice import calibrate
    from askr.voice.listener import MicListener, Segmenter
    from askr.voice.speaker import Speaker
    from askr.voice.stt import Transcriber
    from askr.voice.talker import Talker
    from askr.voice.ui import Display
    from askr.voice.wake import load_profile

    display = Display()
    display.line("info", f"askr voice — project {project}")
    display.status("loading speech model…")
    transcriber = Transcriber()

    profile = load_profile()
    if "calibrate" in args or "calibrated_at" not in profile:
        profile = calibrate.run(transcriber, display)
        if "calibrate" in args:
            return

    listener = MicListener(segmenter=Segmenter(min_rms=profile.get("min_rms", 0.004)))
    gate = WakeGate(variants=profile.get("variants", []))
    speaker = Speaker(listener=listener, gate=gate)
    VoiceLoop(project, listener, transcriber, Talker(), speaker,
              session_id=session_id, display=display).run()
