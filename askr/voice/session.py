"""
What the target Claude Code session is doing, read from its transcript tail.
The talker needs this to answer "what's it doing?" and to decide whether a
spoken input is a new task or extra context for the turn already running.
"""

import json
import os
import re
from dataclasses import dataclass, field

_TAIL_BYTES = 2 * 1024 * 1024


@dataclass
class Digest:
    in_flight: bool = False             # a turn is running right now
    last_prompt: str = ""               # the user's latest typed/sent prompt
    recent_text: list = field(default_factory=list)   # latest assistant prose, oldest first
    recent_tools: list = field(default_factory=list)  # "Bash: npm test", oldest first

    def render(self) -> str:
        lines = [f"Turn running: {'yes' if self.in_flight else 'no (waiting for the user)'}"]
        if self.last_prompt:
            lines.append(f"Last request: {self.last_prompt}")
        if self.recent_tools:
            lines.append("Recent tool calls:\n" + "\n".join(f"- {t}" for t in self.recent_tools))
        if self.recent_text:
            lines.append("Recent assistant messages:\n" + "\n".join(f"- {t}" for t in self.recent_text))
        return "\n".join(lines)


def _tail_entries(transcript_path: str) -> list:
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - _TAIL_BYTES))
            raw = f.read().splitlines()
    except OSError:
        return []
    entries = []
    for line in raw:
        try:
            entries.append(json.loads(line))
        except Exception:
            continue  # partial first line of the tail window
    return entries


def _clip(text: str, n: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _tool_summary(block: dict) -> str:
    inp = block.get("input") or {}
    detail = (inp.get("description") or inp.get("command") or inp.get("file_path")
              or inp.get("pattern") or inp.get("prompt") or "")
    return f"{block.get('name', '?')}: {_clip(str(detail), 100)}"


def is_user_prompt(entry: dict) -> bool:
    """A real user prompt — not a tool result, and not Claude Code's injected meta text."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return not content.startswith("<")
    if isinstance(content, list):
        return any(b.get("type") == "text" and not b.get("text", "").startswith("<")
                   for b in content if isinstance(b, dict))
    return False


def prompt_text(entry: dict) -> str:
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content
                    if isinstance(b, dict) and b.get("type") == "text")


def digest(transcript_path: str, max_text: int = 4, max_tools: int = 8) -> Digest:
    d = Digest()
    entries = _tail_entries(transcript_path)
    for entry in entries:
        kind = entry.get("type")
        if kind == "system" and entry.get("subtype") == "turn_duration":
            d.in_flight = False
        elif kind in ("user", "assistant", "api-request"):
            d.in_flight = True
        if is_user_prompt(entry):
            d.last_prompt = _clip(prompt_text(entry), 300)
        if kind == "assistant":
            for block in (entry.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and block.get("text", "").strip():
                    d.recent_text.append(_clip(block["text"], 400))
                elif block.get("type") == "tool_use":
                    d.recent_tools.append(_tool_summary(block))
    d.recent_text = d.recent_text[-max_text:]
    d.recent_tools = d.recent_tools[-max_tools:]
    return d


def find_latest_transcript(project_path: str) -> str | None:
    """Most recently written transcript for this project — the session being talked to."""
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(project_path))
    folder = os.path.expanduser(f"~/.claude/projects/{slug}")
    try:
        files = [os.path.join(folder, f) for f in os.listdir(folder) if f.endswith(".jsonl")]
    except OSError:
        return None
    return max(files, key=os.path.getmtime) if files else None
