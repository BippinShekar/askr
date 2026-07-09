import fcntl
import json
import os
import platform
import re
import shutil
import subprocess
from datetime import datetime, timezone

_VOICE_LOCK_PATH = os.path.expanduser("~/.config/askr/voice.lock")
_VOICE_LOG_PATH  = os.path.expanduser("~/.config/askr/voice_log.jsonl")

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


def _acquire_voice_lock():
    """
    Serialize spoken output across processes. speak()/announce() are called
    from entirely separate OS processes with no shared state — the daemon's
    trigger thread, the per-turn background handover's detached "Done" ping,
    and hook processes can all decide to speak within moments of each other.
    Without a shared lock, two `say` invocations landing close together play
    concurrently and audibly overlap on macOS, which is what garbles into
    "yapping nonsense" — this forces them to queue and play one at a time.
    flock is tied to the open fd/process, so a crashed holder releases it
    automatically; nothing can deadlock this permanently.
    """
    os.makedirs(os.path.dirname(_VOICE_LOCK_PATH), exist_ok=True)
    fd = open(_VOICE_LOCK_PATH, "w")
    fcntl.flock(fd, fcntl.LOCK_EX)
    return fd


def _release_voice_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except Exception:
        pass


def _log_voice_event(text: str, spoken: bool, reason: str, context: dict = None):
    """
    Append-only log of every spoken-output attempt — not just successful
    ones. Found 2026-07-09: repeated/missing voice announcements were
    diagnosed purely by reading code and inferring a mechanism, with no way
    to confirm which of several candidate call sites actually fired, how
    many times, or why a promised follow-up (e.g. "opening a new chat")
    never visibly happened. This makes that a disk lookup instead of a guess:
    every call records the exact text, whether `say` actually ran (vs. was
    gated off — disabled, non-macOS, no `say` binary, or a subprocess
    failure — each with its own `reason`), and whatever caller context
    (source/session_id/project_path) was passed in.
    """
    try:
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "text": text,
            "spoken": spoken,
            "reason": reason,
        }
        if context:
            entry.update({k: v for k, v in context.items() if v})
        os.makedirs(os.path.dirname(_VOICE_LOG_PATH), exist_ok=True)
        with open(_VOICE_LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def speak(text: str, voice: str = "", context: dict = None) -> tuple[bool, str]:
    """
    Speak text aloud via macOS's native `say` command.
    Gated by the user's voice_notifications preference. Returns (True, "") on
    success, (False, reason) on failure — never raises, since a broken TTS
    call should never take down a hook. `voice` selects a specific macOS
    voice (e.g. "Zarvox"); empty uses the system default. `context` is an
    optional dict (source/session_id/project_path/...) recorded alongside
    this call in voice_log.jsonl for debugging — see _log_voice_event.
    """
    if not text:
        return False, "empty text"

    say_bin, reason = _say_preconditions()
    if not say_bin:
        _log_voice_event(text, False, reason, context)
        return False, reason

    lock_fd = _acquire_voice_lock()
    try:
        cmd = [say_bin]
        if voice:
            cmd += ["-v", voice]
        cmd.append(humanize_for_speech(text))
        subprocess.run(cmd, timeout=30, check=False)
        _log_voice_event(text, True, "", context)
        return True, ""
    except Exception as e:
        _log_voice_event(text, False, str(e), context)
        return False, str(e)
    finally:
        _release_voice_lock(lock_fd)


def speak_signature(prefix: str, body: str, prefix_voice: str, body_voice: str, context: dict = None) -> tuple[bool, str]:
    """
    Speak a short branded prefix in one voice immediately followed by the
    detail in a second voice — askr's two-tone "sonic logo" for the
    session-done ping, distinct from any single generic TTS voice.

    Locked as a single unit so another process's announcement can never land
    between the prefix and body — that interleaving would sound just as
    garbled as two full announcements overlapping. `context` — see speak().
    """
    say_bin, reason = _say_preconditions()
    if not say_bin:
        _log_voice_event(f"{prefix} {body}".strip(), False, reason, context)
        return False, reason

    lock_fd = _acquire_voice_lock()
    try:
        if prefix:
            subprocess.run([say_bin, "-v", prefix_voice, humanize_for_speech(prefix)], timeout=30, check=False)
        if body:
            subprocess.run([say_bin, "-v", body_voice, humanize_for_speech(body)], timeout=30, check=False)
        _log_voice_event(f"{prefix} {body}".strip(), True, "", context)
        return True, ""
    except Exception as e:
        _log_voice_event(f"{prefix} {body}".strip(), False, str(e), context)
        return False, str(e)
    finally:
        _release_voice_lock(lock_fd)


def announce(message: str, prefix: str = "Askr.", context: dict = None) -> tuple[bool, str]:
    """
    The single entry point every askr hook/daemon should call to speak —
    keeps all spoken output on the same voice(s) instead of some call sites
    using the configured sonic logo and others falling back to the system
    default. Honors the user's voice_mode: "dual" speaks `prefix` then
    `message` as the two-tone signature; "single" speaks `message` alone in
    one configured voice. `context` — see speak().
    """
    from askr.state.config import load_voice_mode, load_voice_single, load_voice_prefix, load_voice_body
    if load_voice_mode() == "single":
        return speak(message, voice=load_voice_single(), context=context)
    return speak_signature(prefix, message, load_voice_prefix(), load_voice_body(), context=context)
