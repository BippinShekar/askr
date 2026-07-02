import platform
import re
import shutil
import subprocess

_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "]+"
)
_MARKDOWN_RE = re.compile(r"[*_`~#]")
_TOOL_CALL_RE = re.compile(r"\b([A-Z][A-Za-z]+)\([^)]{0,300}\)")
_WHITESPACE_RE = re.compile(r"\s+")
_NEWLINE_RE = re.compile(r"\s*\n\s*")


def humanize_for_speech(text: str, max_len: int = 200) -> str:
    """
    Turn a written notification string into something pleasant for `say` to
    read aloud — strips emoji/markdown noise, collapses tool-call syntax
    (e.g. "Bash(rm -rf ...)") into plain wording, and caps length at a
    sentence boundary. The written copy (Discord, notification.json, logs)
    is never touched by this — only the duplicate that reaches `say`.
    """
    if not text:
        return text
    text = _EMOJI_RE.sub("", text)
    text = _TOOL_CALL_RE.sub(lambda m: f"a {m.group(1).lower()} action", text)
    text = _MARKDOWN_RE.sub("", text)
    text = _NEWLINE_RE.sub(". ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        cut = text[:max_len]
        last_period = cut.rfind(". ")
        text = cut[: last_period + 1] if last_period > 40 else cut[: max_len - 1].rstrip() + "…"
    return text


def speak(text: str) -> tuple[bool, str]:
    """
    Speak text aloud via macOS's native `say` command.
    Gated by the user's voice_notifications preference. Returns (True, "") on
    success, (False, reason) on failure — never raises, since a broken TTS
    call should never take down a hook.
    """
    try:
        from askr.state.config import load_voice_enabled
        if not load_voice_enabled():
            return False, "voice notifications disabled"
    except Exception as e:
        return False, str(e)

    if platform.system() != "Darwin":
        return False, "voice notifications are macOS-only"

    say_bin = shutil.which("say")
    if not say_bin:
        return False, "'say' not found on PATH"

    try:
        subprocess.run([say_bin, humanize_for_speech(text)], timeout=30, check=False)
        return True, ""
    except Exception as e:
        return False, str(e)
