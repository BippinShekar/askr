"""
Answering Claude Code's permission prompts by voice.

The prompt ("Do you want to proceed? 1. Yes / 2. Yes, and always allow … /
… / No") was driven live on 2026-11-25 in a pty: Enter approves (option 1
is highlighted), Down+Enter approves and always allows, Esc denies.

Keys only go out while the session's transcript still shows the tool call
waiting with no result. Otherwise a late "yes" after the user already
clicked would land in the empty prompt — harmless for Enter, but Down there
recalls the previous message and Enter would re-send it.
"""

import re

from askr.voice.menu import DOWN, ENTER

ESC = "\x1b"
KEYS = {"yes": [ENTER], "always": [DOWN, ENTER], "no": [ESC]}

_ALWAYS = re.compile(r"\b(always|don't ask( me)? again|every time|for good)\b", re.I)
_NO = re.compile(r"^\W*(no|nope|nah|deny|don't|do not|stop|cancel|reject|hold on|wait)\b", re.I)
_YES = re.compile(r"^\W*(yes|yeah|yep|yup|sure|ok(ay)?|go ahead|go for it|do it|approve|allow( it)?|"
                  r"run it|let it|fine|sounds good|send it|ship it)\b", re.I)


def pending_tool(entries: list) -> dict | None:
    """The newest tool call with no result yet — what a permission prompt is asking about."""
    calls, done = {}, set()
    for entry in entries:
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                calls[block.get("id")] = block
            elif block.get("type") == "tool_result":
                done.add(block.get("tool_use_id"))
    waiting = [b for tid, b in calls.items() if tid not in done]
    return waiting[-1] if waiting else None


def describe(block: dict | None) -> str:
    """'run npm test', 'edit app.py', 'use WebFetch' — short enough to say out loud."""
    if not block:
        return ""
    name, inp = block.get("name", ""), block.get("input") or {}
    if name == "Bash":
        what = inp.get("description") or inp.get("command") or ""
        what = " ".join(str(what).split())
        return f"run {what[:60]}" if what else "run a command"
    if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = str(inp.get("file_path") or inp.get("notebook_path") or "")
        return f"edit {path.rsplit('/', 1)[-1]}" if path else "edit a file"
    if name in ("WebFetch", "WebSearch"):
        return "go on the web"
    return f"use {name}" if name else ""


def classify(said: str) -> str | None:
    """'yes' | 'always' | 'no' from a plain reply, or None if it isn't one."""
    said = (said or "").strip()
    if not said or len(said.split()) > 8:
        return None
    # "always" first: "don't ask again" starts like a no.
    if _ALWAYS.search(said) and not re.search(r"^\W*(no|nope|nah)\b", said, re.I):
        return "always"
    if _NO.search(said):
        return "no"
    if _YES.search(said):
        return "yes"
    return None
