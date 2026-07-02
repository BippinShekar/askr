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


def _say_preconditions() -> tuple[str, str]:
    """Shared gate for any spoken output: voice_notifications on, macOS, `say` on PATH.
    Returns (say_bin, "") when clear to speak, ("", reason) otherwise."""
    try:
        from askr.state.config import load_voice_enabled
        if not load_voice_enabled():
            return "", "voice notifications disabled"
    except Exception as e:
        return "", str(e)

    if platform.system() != "Darwin":
        return "", "voice notifications are macOS-only"

    say_bin = shutil.which("say")
    if not say_bin:
        return "", "'say' not found on PATH"

    return say_bin, ""


def speak(text: str, voice: str = "") -> tuple[bool, str]:
    """
    Speak text aloud via macOS's native `say` command.
    Gated by the user's voice_notifications preference. Returns (True, "") on
    success, (False, reason) on failure — never raises, since a broken TTS
    call should never take down a hook. `voice` selects a specific macOS
    voice (e.g. "Zarvox"); empty uses the system default.
    """
    if not text:
        return False, "empty text"

    say_bin, reason = _say_preconditions()
    if not say_bin:
        return False, reason

    try:
        cmd = [say_bin]
        if voice:
            cmd += ["-v", voice]
        cmd.append(humanize_for_speech(text))
        subprocess.run(cmd, timeout=30, check=False)
        return True, ""
    except Exception as e:
        return False, str(e)


def speak_signature(prefix: str, body: str, prefix_voice: str, body_voice: str) -> tuple[bool, str]:
    """
    Speak a short branded prefix in one voice immediately followed by the
    detail in a second voice — askr's two-tone "sonic logo" for the
    session-done ping, distinct from any single generic TTS voice.
    """
    say_bin, reason = _say_preconditions()
    if not say_bin:
        return False, reason

    try:
        if prefix:
            subprocess.run([say_bin, "-v", prefix_voice, humanize_for_speech(prefix)], timeout=30, check=False)
        if body:
            subprocess.run([say_bin, "-v", body_voice, humanize_for_speech(body)], timeout=30, check=False)
        return True, ""
    except Exception as e:
        return False, str(e)


def announce(message: str, prefix: str = "Askr.") -> tuple[bool, str]:
    """
    The single entry point every askr hook/daemon should call to speak —
    keeps all spoken output on the same voice(s) instead of some call sites
    using the configured sonic logo and others falling back to the system
    default. Honors the user's voice_mode: "dual" speaks `prefix` then
    `message` as the two-tone signature; "single" speaks `message` alone in
    one configured voice.
    """
    from askr.state.config import load_voice_mode, load_voice_single, load_voice_prefix, load_voice_body
    if load_voice_mode() == "single":
        return speak(message, voice=load_voice_single())
    return speak_signature(prefix, message, load_voice_prefix(), load_voice_body())
