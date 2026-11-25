"""
The voice assistant as a small tool-using agent on the direct Claude call
(askr.clients.claude._post_messages — the user's subscription, no Claude Code
harness in between).

Every utterance starts with only the user's words and the spoken
conversation so far. Context is loaded on demand through tools — the
session's status or recent output, web search — instead of a session digest
pre-loaded into every call (the old Talker), and simple errands are done
right here (open a link, look something up). Only genuinely multi-step work
on a computer goes to a separate background `claude -p` (delegate_task).

The agent's final text is what gets spoken.
"""

import json
import subprocess
from dataclasses import dataclass, field

from askr.voice.style import SILENT, VOICE_STYLE
from askr.voice.talker import VOICE_MODEL

MAX_STEPS = 6
_MAX_HISTORY = 12

SYSTEM = """You are askr's voice: the user talks to you out loud while they work with Claude Code (a coding agent running in their terminal, "the session"). You hear them through local speech-to-text, so fix obvious mishearings from context ("link" → "lint", "get" → "git").

You start with only their words. Load context only when you need it:
- session_status: what the session is doing / did last. Call it for questions about progress, or when an instruction is ambiguous without it. Don't call it for errands that have nothing to do with the session.
- web_search: facts, links, anything current.

Act with tools:
- send_to_session: hand an instruction to the coding session — anything about its code, project or current work, or anything that refers to "it"/"this". Write it as a clear instruction in the user's voice, keeping every detail they gave. Never hold an instruction back because it seems unrelated to the current work; that's their call.
- open_url: open a page or video in their browser. Always get the URL from web_search results first — never type a video or page URL from memory.
- start_dictation: they want what they say next written into Apple Notes ("transcribe what I say into Notes", "take notes").
- delegate_task: heavy orchestration and execution — anything that needs a full coding agent working inside a project (reading or changing its code, running its commands, multi-step research write-ups about it) when that project isn't the open session's. Set "project" to the project folder name (their projects live in ~/Desktop/<name>, e.g. "leaps") so the agent runs inside it; leave it out only for work tied to no project. Never ask what a project is — the agent can read it. Its result is spoken later.
Rule of thumb: answering, looking up, opening, dictating and passing instructions are quick and direct — do them yourself. Work on the open session's project goes to send_to_session. Work on any other project goes to delegate_task.
A clear instruction goes straight to send_to_session — never call session_status first, and never hold it back because the session is busy: it's queued and Claude Code picks it up mid-turn. Do simple errands yourself. Ask one short question only if a request is genuinely ambiguous and nothing you or a background agent could look up would resolve it.

Decide whether to speak, act, or both:
- Act and stay quiet when the result speaks for itself — they asked to open something and it opened, or you typed an instruction into the terminal they're looking at. Reply exactly (silent).
- Act and speak when they can't see the outcome or need to know something: you answered a question, you started something in the background ("on it, I'll tell you when it's done"), or a tool returned an error — always tell them what failed, briefly, in the error's own terms; never guess a cause it didn't give ("couldn't find its terminal", not "the session crashed").
- Only speak when they asked something you can answer, or you need one detail from them.
Don't invent progress you didn't read with session_status.

""" + VOICE_STYLE

TOOLS = [
    {"name": "session_status",
     "description": "What the Claude Code session in the user's terminal is doing: whether a turn is running, "
                    "the last request, recent tool calls and assistant messages. detail=true returns more.",
     "input_schema": {"type": "object", "properties": {"detail": {"type": "boolean"}}}},
    {"name": "send_to_session",
     "description": "Send an instruction to the Claude Code session (typed into its terminal, or queued if it's busy).",
     "input_schema": {"type": "object", "properties": {"instruction": {"type": "string"}},
                      "required": ["instruction"]}},
    {"name": "open_url",
     "description": "Open a URL in the user's default browser.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "start_dictation",
     "description": "Start writing everything the user says next into a new Apple Notes note (opens Notes).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "delegate_task",
     "description": "Run a multi-step errand in a separate background agent; its result is spoken when done. "
                    "The task must be self-contained — the agent sees nothing of this conversation.",
     "input_schema": {"type": "object", "properties": {
         "task": {"type": "string"},
         "project": {"type": "string", "description": "Project folder to run in, e.g. 'leaps' (~/Desktop/leaps)."}},
         "required": ["task"]}},
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 3},
]


@dataclass
class Turn:
    say: str
    actions: list = field(default_factory=list)  # (tool name, input) for each client tool called


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "error: only http(s) URLs can be opened"
    r = subprocess.run(["open", url], capture_output=True, text=True, timeout=10)
    return "opened" if r.returncode == 0 else f"error: {r.stderr.strip()[:200]}"


class VoiceAgent:
    """`handlers` maps client tool names to callables(input dict) -> str, so the
    voice loop decides what each action actually does (and tests can fake them)."""

    def __init__(self, handlers: dict, post=None, model: str = VOICE_MODEL):
        if post is None:
            from askr.clients.claude import _post_messages as post
        self._post = post
        self.model = model
        self.handlers = handlers
        self.history: list = []

    def respond(self, utterance: str, extra_context: str = "") -> Turn:
        said = utterance if not extra_context else f"{utterance}\n\n({extra_context})"
        messages = self.history + [{"role": "user", "content": said}]
        actions = []
        text = ""
        for _ in range(MAX_STEPS):
            try:
                data = self._post({"model": self.model, "max_tokens": 600, "system": SYSTEM,
                                   "tools": TOOLS, "messages": messages}, "voice_agent", utterance[:80])
            except Exception as e:
                from askr.utils.logger import log_error
                log_error("voice.agent", str(e))
                return Turn("I couldn't reach Claude just now.", actions)
            content = data.get("content") or []
            text = " ".join(b.get("text", "") for b in content if b.get("type") == "text").strip()
            calls = [b for b in content if b.get("type") == "tool_use"]
            if not calls:
                break
            messages = messages + [{"role": "assistant", "content": content}]
            results = []
            for call in calls:
                name, inp = call.get("name"), call.get("input") or {}
                handler = self.handlers.get(name)
                try:
                    out = handler(inp) if handler else f"error: unknown tool {name}"
                except Exception as e:
                    out = f"error: {e}"
                actions.append((name, inp))
                results.append({"type": "tool_result", "tool_use_id": call.get("id"), "content": str(out)[:4000]})
            messages = messages + [{"role": "user", "content": results}]
        say = text if text else ("" if actions else "Sorry, didn't catch that.")
        if say.strip() == SILENT:
            say = ""
        # Keep only the spoken exchange: tool output (session status, search
        # results) goes stale and would crowd every later call.
        self.history = (self.history + [
            {"role": "user", "content": utterance},
            {"role": "assistant", "content": (say or SILENT) + _action_note(actions)},
        ])[-_MAX_HISTORY:]
        return Turn(say, actions)

    def note_update(self, spoken: str):
        """A spoken session update, so follow-ups ("why did it fail?") have context."""
        self.history = (self.history + [
            {"role": "user", "content": "(session update — not said by the user)"},
            {"role": "assistant", "content": spoken},
        ])[-_MAX_HISTORY:]


def _action_note(actions: list) -> str:
    if not actions:
        return ""
    return " [did: " + "; ".join(f"{n} {json.dumps(i)[:120]}" for n, i in actions) + "]"
