"""
Watches the target session's transcript and decides what's worth saying.

- done:     a turn finished — speak its final message.
- question: Claude is asking the user something (AskUserQuestion) — speak it,
            since the user may not be looking at the screen.
- progress: a long turn wrote new prose — speak it, at most every
            PROGRESS_EVERY_SECS, so a 20-minute task isn't silent but
            isn't a running commentary either.
"""

import json
import os
from dataclasses import dataclass

PROGRESS_EVERY_SECS = 90.0


@dataclass
class Event:
    kind: str  # "done" | "question" | "progress"
    text: str


class Narrator:
    def __init__(self, transcript_path: str, progress_every: float = PROGRESS_EVERY_SECS):
        self.path = transcript_path
        self.progress_every = progress_every
        self._offset = os.path.getsize(transcript_path) if os.path.exists(transcript_path) else 0
        self._partial = b""
        self._last_text = ""
        self._unspoken_progress = ""
        self._last_spoken_at = 0.0

    def _new_entries(self) -> list:
        try:
            with open(self.path, "rb") as f:
                f.seek(self._offset)
                chunk = f.read()
        except OSError:
            return []
        self._offset += len(chunk)
        data = self._partial + chunk
        lines = data.split(b"\n")
        self._partial = lines.pop()  # incomplete last line, finished next poll
        entries = []
        for line in lines:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
        return entries

    def poll(self, now: float) -> list:
        events = []
        for entry in self._new_entries():
            kind = entry.get("type")
            if kind == "assistant":
                for block in (entry.get("message") or {}).get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        self._last_text = block["text"].strip()
                        self._unspoken_progress = self._last_text
                    elif block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
                        qs = (block.get("input") or {}).get("questions") or []
                        text = " ".join(q.get("question", "") for q in qs if isinstance(q, dict)).strip()
                        if text:
                            events.append(Event("question", text))
            elif kind == "system" and entry.get("subtype") == "turn_duration":
                if self._last_text:
                    events.append(Event("done", self._last_text))
                self._last_text = self._unspoken_progress = ""

        if events:
            self._last_spoken_at = now
        elif self._unspoken_progress and now - self._last_spoken_at >= self.progress_every:
            events.append(Event("progress", self._unspoken_progress))
            self._unspoken_progress = ""
            self._last_spoken_at = now
        return events

    def mark_spoken(self, now: float):
        """The talker just spoke — progress throttle restarts from here."""
        self._last_spoken_at = now
