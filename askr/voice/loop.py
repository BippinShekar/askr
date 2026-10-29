"""
`askr voice` — talk to the Claude Code session running in this project.

  mic -> Segmenter -> Whisper -> WakeGate -> Talker ─┬─ say  -> Speaker
                                                     └─ send -> terminal (or Stop-hook inbox)
  session transcript -> Narrator -> Talker.narrate -> Speaker
"""

import os
import queue
import time

from askr.voice import inbox, session, terminal
from askr.voice.narrator import Narrator
from askr.voice.wake import WakeGate

_RETARGET_EVERY_SECS = 10.0
_CLAIM_TIMEOUT_SECS = 6.0


class VoiceLoop:
    def __init__(self, project_path: str, listener, transcriber, talker, speaker,
                 session_id: str = "", out=print, clock=time.time):
        self.project_path = project_path
        self.listener = listener
        self.transcriber = transcriber
        self.talker = talker
        self.speaker = speaker
        self.gate = speaker.gate or WakeGate()
        self.pinned_session = session_id
        self.out = out
        self.clock = clock
        self.transcript_path = ""
        self.narrator = None
        self.last_request = ""
        self._last_retarget = 0.0

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
            self.out(f"→ talking to session {self.session_id[:8]}")

    # --- one utterance ---------------------------------------------------

    def handle_utterance(self, audio):
        text = self.transcriber.transcribe(audio)
        if not text:
            return
        command = self.gate.accept(text, self.clock())
        if command is None:
            self.out(f"  (ignored) {text}")
            return
        self.out(f"you: {command}")
        if not self.transcript_path:
            self.speaker.speak("I can't find a Claude Code session in this project.")
            return
        d = session.digest(self.transcript_path)
        reply = self.talker.respond(command, d.render())
        self.out(f"askr: {reply.say}" + (f"\n  → claude: {reply.send}" if reply.send else ""))
        self.speaker.speak(reply.say)
        if self.narrator:
            self.narrator.mark_spoken(self.clock())
        if reply.send:
            self.last_request = reply.send
            self.deliver(reply.send, d.in_flight)

    def deliver(self, text: str, in_flight: bool):
        if terminal.type_prompt(self.session_id, text, self.project_path) and self._claimed():
            return
        if in_flight:
            inbox.post(self.session_id, text)
            self.out("  (terminal not found — queued for the end of this turn)")
            self.speaker.speak("I couldn't reach its terminal, so it'll get that when it finishes this step.")
        else:
            self.out("  (terminal not found — not delivered)")
            self.speaker.speak("I couldn't find that session's terminal. Is the askr extension running in Cursor?")

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

    # --- narration -------------------------------------------------------

    def narrate(self):
        if not self.narrator:
            return
        for event in self.narrator.poll(self.clock()):
            spoken = self.talker.narrate(event.text, self.last_request) or event.text
            if event.kind == "question":
                spoken = f"It's asking: {spoken}"
            self.out(f"askr ({event.kind}): {spoken}")
            self.speaker.speak(spoken)
            self.talker.note_update(spoken)

    # --- main loop -------------------------------------------------------

    def run_once(self, wait: float = 0.5):
        self.retarget()
        try:
            audio = self.listener.utterances.get(timeout=wait)
        except queue.Empty:
            audio = None
        if audio is not None:
            self.handle_utterance(audio)
        self.narrate()

    def run(self):
        self.retarget(force=True)
        self.listener.start()
        self.out('listening — start with "askr …"; Ctrl+C to stop')
        try:
            while True:
                self.run_once()
        except KeyboardInterrupt:
            self.out("\nstopped")
        finally:
            self.listener.stop()


def main(args: list):
    session_id = ""
    if "--session" in args:
        i = args.index("--session")
        session_id = args[i + 1] if i + 1 < len(args) else ""

    from askr.session.monitor import find_project_root
    from askr.voice.listener import MicListener
    from askr.voice.speaker import Speaker
    from askr.voice.stt import Transcriber
    from askr.voice.talker import Talker

    project = find_project_root() or os.getcwd()
    print("loading speech model (first run downloads ~140 MB)…")
    transcriber = Transcriber()
    listener = MicListener()
    gate = WakeGate()
    speaker = Speaker(listener=listener, gate=gate)
    VoiceLoop(project, listener, transcriber, Talker(), speaker, session_id=session_id).run()
