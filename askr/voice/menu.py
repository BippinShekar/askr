"""
Answering Claude Code's option menus (AskUserQuestion) by voice.

While a menu is up the session is blocked on it, so a spoken reply has to
become keystrokes in the menu, not a typed prompt. Verified against a live
Claude Code session on 2026-11-01 (pty-driven):

- each question starts with option 1 highlighted; Down ×(n-1) then Enter
  picks option n;
- free text: Down to "Type something" (the row after the last option), type,
  Enter;
- with several questions, answering one moves to the next, and a final
  "Submit answers" screen (option 1) needs one more Enter. A single question
  has no submit screen.

Multi-select menus aren't driven by voice — their keys weren't verified, and
a wrong toggle is worse than asking the user to click.
"""

import json
import re

DOWN, ENTER = "\x1b[B", "\r"

_ORDINALS = {"first": 1, "one": 1, "1": 1, "second": 2, "two": 2, "2": 2, "third": 3, "three": 3,
             "3": 3, "fourth": 4, "four": 4, "4": 4, "fifth": 5, "five": 5, "5": 5}
_LAST = {"last", "final", "bottom"}


def pending_questions(entries: list) -> list | None:
    """Questions of an AskUserQuestion call with no tool_result yet, else None."""
    pending, answered = {}, set()
    for entry in entries:
        content = (entry.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
                pending[block.get("id")] = (block.get("input") or {}).get("questions") or []
            elif block.get("type") == "tool_result":
                answered.add(block.get("tool_use_id"))
    open_ = [qs for tid, qs in pending.items() if tid not in answered]
    return open_[-1] if open_ else None


def render(questions: list) -> str:
    lines = []
    for i, q in enumerate(questions, 1):
        lines.append(f"Q{i}: {q.get('question', '')}" + ("  (multi-select)" if q.get("multiSelect") else ""))
        for j, opt in enumerate(q.get("options") or [], 1):
            lines.append(f"  {j}. {opt.get('label', '')} — {opt.get('description', '')}")
    return "\n".join(lines)


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


def quick_pick(utterance: str, options: list) -> int | None:
    """Option number from an unambiguous reply ("the second one", "option 3",
    "Nova", "last one"); None when it needs the model."""
    said = _norm(utterance)
    words = said.split()
    if not words or len(words) > 6:
        return None
    labels = [_norm(o.get("label", "")).replace(" recommended", "") for o in options]
    hits = [i for i, label in enumerate(labels, 1) if label and re.search(rf"\b{re.escape(label)}\b", said)]
    if len(hits) == 1:
        return hits[0]
    if set(words) & _LAST:
        return len(options)
    nums = {_ORDINALS[w] for w in words if w in _ORDINALS and w.endswith(("st", "nd", "rd", "th"))}
    if not nums:  # "second one": the ordinal decides; "one" there is not a number
        nums = {_ORDINALS[w] for w in words if w in _ORDINALS}
    if len(nums) == 1 and min(nums) <= len(options):
        return min(nums)
    return None


PICK_SYSTEM = """The user is answering an on-screen multiple-choice menu by voice. Map what they said to answers.
Reply with only JSON: {"answers": [...one per question, in order...], "say": "<short spoken confirmation, under 12 words>"}
Each answer is {"choice": <option number>} when they picked (or clearly meant) a listed option,
{"other": "<their answer, cleaned up>"} when they gave their own answer instead, or null if they
didn't address that question. If they're not answering the menu at all (talking about something
else, asking a question), reply {"answers": null, "say": ""}."""


def model_pick(post, model: str, utterance: str, questions: list) -> tuple:
    """(answers, say) via the model; answers None when the utterance isn't an answer."""
    data = post({
        "model": model,
        "max_tokens": 300,
        "system": PICK_SYSTEM,
        "messages": [{"role": "user", "content": f"Menu:\n{render(questions)}\n\nUser said: {utterance}"}],
    }, "voice_menu", utterance[:80])
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        out = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        out = {}
    return out.get("answers"), str(out.get("say") or "").strip()


def keys_for(questions: list, answers: list) -> list | None:
    """Keystrokes for the menu, or None if it can't be answered safely by voice."""
    if any(q.get("multiSelect") for q in questions) or len(answers) != len(questions):
        return None
    keys = []
    for q, a in zip(questions, answers):
        n = len(q.get("options") or [])
        if not isinstance(a, dict):
            return None
        if "choice" in a:
            try:
                choice = int(a["choice"])
            except (TypeError, ValueError):
                return None
            if not 1 <= choice <= n:
                return None
            keys += [DOWN] * (choice - 1) + [ENTER]
        elif str(a.get("other") or "").strip():
            keys += [DOWN] * n + [str(a["other"]).strip(), ENTER]
        else:
            return None
    if len(questions) > 1:
        keys.append(ENTER)  # "Submit answers"
    return keys


def describe(questions: list, answers: list) -> str:
    parts = []
    for q, a in zip(questions, answers):
        if "choice" in a:
            parts.append((q.get("options") or [])[int(a["choice"]) - 1].get("label", ""))
        else:
            parts.append(f"“{a['other']}”")
    return ", ".join(parts)
