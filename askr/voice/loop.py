"""
`askr voice` — talk to the Claude Code session running in this project.

  mic -> Segmenter -> Whisper -> WakeGate -> Talker ─┬─ say  -> Speaker
                                                     └─ send -> terminal (or Stop-hook inbox)
  session transcript -> Narrator -> Talker.narrate -> Speaker

Normally runs in the background (daemon.py), started by the askr IDE
extension, which shows its status in the status bar and types requests into
the focused Claude Code terminal. `askr voice --here` runs it in the current
terminal instead, with a live status line — for debugging.
"""

import os
import queue
import signal
import threading
import time

from askr.voice import agent as agent_mod
from askr.voice import inbox, menu, notes, session, tasks, terminal
from askr.voice.agent import VoiceAgent
from askr.voice.narrator import Narrator
from askr.voice.talker import VOICE_MODEL
from askr.voice.wake import WakeGate

_RETARGET_EVERY_SECS = 10.0
_CLAIM_TIMEOUT_SECS = 6.0
_PARTIAL_EVERY_SECS = 1.0
# Partials only transcribe the tail: with a video playing an utterance runs
# up to the segmenter's 30s cap, and re-transcribing all of it every second
# would pin a core.
_PARTIAL_TAIL_SECS = 6.0


class _NullDisplay:
    def line(self, kind, text):
        pass

    def status(self, *a, **k):
        pass


class VoiceLoop:
    def __init__(self, project_path: str, listener, transcriber, talker, speaker,
                 session_id: str = "", display=None, clock=time.time, resolve=None,
                 ptt_state=None, mic_off=None, agent=None):
        self.project_path = project_path
        self.listener = listener
        self.transcriber = transcriber
        self.talker = talker
        self.speaker = speaker
        self.gate = speaker.gate or WakeGate()
        self.pinned_session = session_id
        self.display = display or _NullDisplay()
        self.clock = clock
        self.resolve = resolve  # () -> transcript path; default: newest in project_path
        self.ptt_state = ptt_state or (lambda: False)  # () -> push-to-talk held?
        self.mic_off = mic_off or (lambda: False)  # () -> user turned the mic off
        self._mic_lock = threading.Lock()
        self.tasks = tasks.Tasks()
        self._menu_open = False
        self.agent = agent or VoiceAgent(self._tool_handlers(), post=getattr(talker, "_post", None))
        self._ptt = None  # list of texts while push-to-talk is recording
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
        if self.resolve and not self.pinned_session:
            path = self.resolve()
        elif self.pinned_session:
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
        save_clip = getattr(self.display, "save_clip", None)
        if save_clip:
            save_clip(audio, text)
        if self._ptt is not None:
            # Push-to-talk: no wake word; collect until the shortcut is pressed again.
            if text:
                self._ptt.append(text)
                self.display.line("you", f"  (push-to-talk) {text}")
            return
        if not text:
            self.display.line("ignored", "  (heard sound, no words)")
            return
        if notes.active() and self.gate.match(text) is None:
            # Dictation: everything heard goes into the note, no wake word, no
            # Claude — except lines addressed to askr, which are still commands.
            if notes.wants_stop(text):
                notes.stop()
                self.display.line("askr", "Stopped taking notes.")
                self._speak("Stopped taking notes.")
            elif notes.append(text):
                self.display.line("notes", text)
            else:
                self.display.line("error", f"  couldn't write to Notes: {text}")
            return
        command = self.gate.accept(text, self.clock())
        if command is None:
            if self.gate.match(text) is not None:
                self.display.line("you", f"{self.gate.word} — listening, go ahead   (heard: {text})")
            else:
                self.display.line("ignored", f"  heard: {text}   ← no wake word, ignored")
            return
        self.display.line("you", command)
        self.handle_command(command)

    def handle_command(self, command: str):
        """Act on something addressed to askr (wake word already stripped)."""
        if notes.active() and notes.wants_stop(command):
            notes.stop()
            self.display.line("askr", "Stopped taking notes.")
            self._speak("Stopped taking notes.")
            return
        if notes.wants_start(command):
            self.start_dictation()
            return
        self.retarget(force=True)  # the terminal focused now, not 10s ago
        self._status("thinking")
        questions = None
        if self.transcript_path:
            questions = menu.pending_questions(session._tail_entries(self.transcript_path))
            if questions is not None and self.answer_menu(command, questions):
                return
        self._menu_open = questions is not None
        extra = ("Claude Code is showing a multiple-choice question and is blocked on it; "
                 "nothing can be sent to the session until it's answered." if self._menu_open else "")
        turn = self.agent.respond(command, extra)
        self.display.line("askr", turn.say)
        self._speak(turn.say)
        if self.narrator:
            self.narrator.mark_spoken(self.clock())

    # --- the agent's tools (askr/voice/agent.py) ------------------------

    def _tool_handlers(self) -> dict:
        return {
            "session_status": self._tool_session_status,
            "send_to_session": self._tool_send,
            "open_url": self._tool_open_url,
            "start_dictation": lambda inp: (self.start_dictation(speak=False), "dictation started; Notes is open")[1],
            "delegate_task": self._tool_delegate,
        }

    def _tool_session_status(self, inp: dict) -> str:
        if not self.transcript_path:
            return "No Claude Code session is open."
        detail = bool(inp.get("detail"))
        return session.digest(self.transcript_path, max_text=8 if detail else 3,
                              max_tools=16 if detail else 6).render()

    def _tool_send(self, inp: dict) -> str:
        text = str(inp.get("instruction") or "").strip()
        if not text:
            return "error: empty instruction"
        if not self.transcript_path:
            return "error: no Claude Code session is open to send that to"
        if self._menu_open:
            # Typed text would land inside the open menu and pick who-knows-what.
            return "error: the session is waiting on its multiple-choice question; it must be answered first"
        self.display.line("claude", f"  → {text}")
        self.last_request = text
        self._status("sending")
        return self.deliver(text, session.digest(self.transcript_path).in_flight)

    def _tool_open_url(self, inp: dict) -> str:
        url = str(inp.get("url") or "")
        self.display.line("task", f"  ⇢ open {url}")
        return agent_mod.open_url(url)

    def _tool_delegate(self, inp: dict) -> str:
        task = str(inp.get("task") or "").strip()
        if not task:
            return "error: empty task"
        self.display.line("task", f"  ⇢ background: {task}")
        self.tasks.start(task)
        return "started in the background; its result will be spoken when it finishes"

    def start_dictation(self, speak: bool = True):
        title = notes.start(self.clock())  # also opens Notes on the new note
        self.display.line("askr", f"Taking notes in Notes → “{title}”. Say “stop taking notes” to end.")
        if speak:
            self._speak("Taking notes. Say stop taking notes when you're done.")

    def report_tasks(self):
        """Speak the outcome of background tasks as they finish."""
        while True:
            try:
                done = self.tasks.finished.get_nowait()
            except queue.Empty:
                return
            self._status("thinking")
            spoken = (self.talker.narrate(done.result, done.task) or done.result) if done.result else ""
            if not done.ok:
                spoken = f"That task didn't work. {spoken}".strip()
            spoken = spoken or "Done."
            self.display.line("task", f"  ✓ {done.task[:60]} — {done.result[:200]}")
            self.display.line("askr", spoken)
            self._speak(spoken)

    def answer_menu(self, command: str, questions: list) -> bool:
        """Answer an open AskUserQuestion menu; False if `command` isn't an answer to it."""
        answers, say = None, ""
        if len(questions) == 1:
            n = menu.quick_pick(command, questions[0].get("options") or [])
            if n:
                answers = [{"choice": n}]
        if answers is None:
            try:
                answers, say = menu.model_pick(self.talker._post, VOICE_MODEL, command, questions)
            except Exception:
                answers = None
        if not answers:
            return False
        keys = menu.keys_for(questions, answers)
        if keys is None:
            self.display.line("askr", "  menu needs picking on screen (multi-select or partial answer)")
            self._speak("I can't fill that one in by voice. Pick it on screen.")
            return True
        picked = menu.describe(questions, answers)
        self.display.line("you", f"  menu → {picked}")
        self._speak(say or f"Picking {picked}.")
        self._status("sending")
        if terminal.type_keys(self.session_id, keys, self.project_path) and self._claimed():
            self.display.line("info", "  selected in the menu")
        else:
            self.display.line("error", "  terminal not found — menu not answered")
            self._speak("I couldn't reach its terminal. Pick it on screen.")
        return True

    def deliver(self, text: str, in_flight: bool) -> str:
        """Hand `text` to the session; returns what happened (the agent tells the user)."""
        if terminal.type_prompt(self.session_id, text, self.project_path) and self._claimed():
            self.display.line("info", "  delivered to the session's terminal")
            return "typed into its terminal"
        if in_flight:
            inbox.post(self.session_id, text)
            self.display.line("error", "  terminal not found — queued for the end of this turn")
            return "queued: its terminal couldn't be reached, so it'll get that when it finishes this step"
        self.display.line("error", "  terminal not found — not delivered")
        return "error: couldn't find that session's terminal — is the askr extension running in Cursor?"

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
            from askr.voice.listener import SAMPLE_RATE
            audio = audio[-int(_PARTIAL_TAIL_SECS * SAMPLE_RATE):]
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
            self.agent.note_update(spoken)

    # --- main loop -------------------------------------------------------

    # --- push-to-talk ------------------------------------------------------

    def poll_ptt(self):
        held = self.ptt_state()
        if held and self._ptt is None:
            self._ptt = []
            self.display.line("info", "push-to-talk: recording — press the shortcut again to send")
        elif not held and self._ptt is not None:
            self.finish_ptt()

    def finish_ptt(self):
        texts, self._ptt = self._ptt or [], []
        # Speech still in progress when the shortcut was pressed: finished
        # utterances queued but not yet handled, then the open segment.
        while True:
            try:
                audio = self.listener.utterances.get_nowait()
            except queue.Empty:
                break
            texts.append(self.transcriber.transcribe(audio))
        seg = getattr(self.listener, "segmenter", None)
        if seg is not None:
            audio = seg.snapshot()
            seg.reset()
            if audio is not None:
                texts.append(self.transcriber.transcribe(audio))
        self._ptt = None
        command = " ".join(t.strip() for t in texts if t and t.strip())
        if not command:
            self.display.line("ignored", "  push-to-talk: heard nothing")
            return
        self.display.line("you", command)
        self.gate.open_window(self.clock())
        self.handle_command(command)

    def poll_mic(self) -> bool:
        """Open or close the mic to match the user's toggle; True if it's off.
        Runs on its own thread (watch_mic) as well as the main loop: the main
        loop can sit 5-10s in a Haiku call, and ⌘M has to act immediately."""
        with self._mic_lock:
            off = self.mic_off()
            running = getattr(self.listener, "running", True)
            if off and running:
                stop_speaking = getattr(self.speaker, "stop", None)
                if stop_speaking:
                    stop_speaking()
                self.listener.stop()
                self._ptt = None
                self._partial = ""
                self.display.line("info", "mic off")
                self._status("mic off")
            elif not off and not running:
                self.listener.start()
                self.display.line("info", "mic on")
                self._status("listening")
            return off

    def watch_mic(self, stop: threading.Event, every: float = 0.2):
        while not stop.wait(every):
            try:
                self.poll_mic()
            except Exception as e:
                self.display.line("error", f"  mic toggle failed: {e}")

    def run_once(self, wait: float = 0.15):
        self.retarget()
        if self.poll_mic():
            # Mic closed: still speak finished tasks and session updates.
            time.sleep(wait)
            self.narrate()
            self.report_tasks()
            self._status("mic off")
            return
        self.poll_ptt()
        try:
            audio = self.listener.utterances.get(timeout=wait)
        except queue.Empty:
            audio = None
        if audio is not None:
            self.handle_utterance(audio)
        else:
            self.update_partial()
        self.narrate()
        self.report_tasks()
        if hasattr(self.display, "tasks_running"):
            self.display.tasks_running = len(self.tasks.running)
        seg = getattr(self.listener, "segmenter", None)
        hearing = bool(seg and seg.active)
        if self._ptt is not None:
            self._status("recording", self._partial if hearing else " ".join(self._ptt)[-80:])
        else:
            self._status("hearing…" if hearing else "listening", self._partial if hearing else "")

    def run(self):
        self.retarget(force=True)
        if not self.mic_off():
            self.listener.start()
        self.display.line("info", f'listening — start with "{self.gate.word} …"   (Ctrl+C to stop)')
        stop = threading.Event()
        threading.Thread(target=self.watch_mic, args=(stop,), daemon=True).start()
        try:
            while True:
                self.run_once()
        except KeyboardInterrupt:
            self.display.line("info", "stopped")
        finally:
            stop.set()
            with self._mic_lock:
                self.listener.stop()


def main(args: list):
    from askr.voice import daemon

    if args[:1] == ["notes"]:
        if args[1:2] == ["off"]:
            notes.stop()
            print("askr voice: stopped taking notes.")
        else:
            print(f"askr voice: taking notes in Notes → {notes.start()}. `askr voice notes off` to stop.")
        return
    if args[:1] == ["wake"]:
        from askr.voice.wake import DEFAULT_WORD, load_profile, save_profile
        profile = load_profile()
        if len(args) < 2:
            print(f"askr voice: wake word is \"{profile.get('wake_word', DEFAULT_WORD)}\". "
                  "`askr voice wake <word or phrase>` to change it.")
            return
        profile["wake_word"] = " ".join(args[1:]).strip()
        save_profile(profile)
        restarted = daemon.stop()
        if restarted:
            daemon.start_detached()
        print(f"askr voice: wake word is now \"{profile['wake_word']}\"" + (" (restarted)." if restarted else "."))
        return
    if args[:1] == ["mic"]:
        daemon.set_mic(args[1:2] != ["off"])
        print(f"askr voice: mic {'off' if daemon.mic_off() else 'on'}.")
        return
    if args[:1] == ["off"]:
        daemon.set_enabled(False)
        daemon.stop()
        print("askr voice: off (the IDE extension won't restart it). `askr voice on` to turn it back on.")
        return
    if args[:1] in (["on"], ["start"]):
        if args[0] == "on":
            daemon.set_enabled(True)
        if daemon.running_pid():
            print("askr voice: already listening in the background.")
        elif daemon.start_detached():
            print("askr voice: listening in the background — status is in the Cursor status bar.")
        else:
            print("askr voice: turned off — `askr voice on` to enable.")
        return

    is_daemon = "--daemon" in args
    lock = None
    if is_daemon:
        if os.path.exists(daemon.DISABLED_PATH):
            return
        lock = daemon.acquire_lock()
        if lock is None:
            return  # another daemon is already listening
        signal.signal(signal.SIGTERM, signal.default_int_handler)  # stop cleanly, like Ctrl+C
    elif daemon.running_pid() and "calibrate" not in args:
        print("askr voice is already listening in the background (status is in the Cursor status bar).\n"
              "`askr voice off` stops it; `askr voice calibrate` tunes it to your voice.")
        return

    session_id = ""
    if "--session" in args:
        i = args.index("--session")
        session_id = args[i + 1] if i + 1 < len(args) else ""

    from askr.session.monitor import find_project_root
    from askr.voice import calibrate
    from askr.voice.listener import MicListener, Segmenter
    from askr.voice.speaker import Speaker
    from askr.voice.stt import Transcriber
    from askr.voice.talker import Talker
    from askr.voice.ui import Display
    from askr.voice.wake import DEFAULT_WORD, load_profile, phrase_key

    project = find_project_root() or os.getcwd()
    display = daemon.StatusFile() if is_daemon else Display()
    profile = load_profile()
    word = profile.get("wake_word") or DEFAULT_WORD
    if is_daemon:
        display.wake = word
    display.status("loading speech model…")
    transcriber = Transcriber(wake_word=word)

    if "calibrate" in args:
        calibrate.run(transcriber, display)
        return

    listener = MicListener(segmenter=Segmenter(min_rms=profile.get("min_rms", 0.004)))
    # Calibration-learned spellings are for "askr"; a chosen word matches on its own.
    learned = profile.get("variants", []) if phrase_key(word) == "askr" else []
    gate = WakeGate(variants=learned, word=word)
    speaker = Speaker(listener=listener, gate=gate)
    try:
        VoiceLoop(project, listener, transcriber, Talker(), speaker, session_id=session_id,
                  display=display, resolve=daemon.target_transcript, ptt_state=daemon.ptt_on,
                  mic_off=daemon.mic_off).run()
    finally:
        if lock is not None:
            display.status("off")
