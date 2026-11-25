"""
How askr sounds when it talks back. One place, shared by the voice agent,
narration and task reports, plus a hard length cap in code — prompts alone
drifted into reading out paragraphs (user feedback 2026-11-25: "talk like a
human, like me … not recite goddamn paras").
"""

import re

VOICE_STYLE = """How you talk (everything you write is read aloud):
- Like the user talks to a friend at their desk: casual, direct, contractions, no politeness padding. "yep, sent it", "tests are running", "it failed — missing env var", "done, it's on main".
- Short. One sentence, two at most, usually under 15 words — even when asked what it's doing: the gist, not a report. Say the one thing that matters; skip what they can already see.
- Never read out lists, paths, code, URLs, numbers with many digits, or markdown.
- No filler openers ("Great", "Sure thing", "I've gone ahead and"), no sign-offs, no recaps of what they just said."""

SILENT = "(silent)"
_MAX_WORDS = 25


def concise(text: str, max_words: int = _MAX_WORDS) -> str:
    """At most two sentences and `max_words` words; markdown and leftovers stripped."""
    text = re.sub(r"[*_`#>]+", "", (text or "")).strip()
    text = re.sub(r"\s+", " ", text)
    if not text or text == SILENT:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    text = " ".join(sentences[:2])
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words]).rstrip(",;:—-") + "…"
    return text
