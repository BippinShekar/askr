import fcntl
import json
import os
import platform
import re
import shutil
import time
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


# ⌘M in the IDE (askr/voice/daemon.py set_mic): askr neither listens nor
# speaks — every spoken output path checks this, not just voice mode.
MUTED_PATH = os.path.expanduser("~/.config/askr/voice_mic_off")


def is_muted() -> bool:
    return os.path.exists(MUTED_PATH)


# One voice and pace for everything askr says (user, 2026-11-25): Ava is the
# main voice, Zoe the alternative (`askr voice speaker zoe`), Samantha the
# fallback until those are downloaded (System Settings → Accessibility →
# Spoken Content → Manage Voices — there's no CLI for it). Premium beats
# Enhanced. 200 wpm is the pace the user picked Samantha at.
VOICES = {
    "ava": ("Ava (Premium)", "Ava (Enhanced)", "Ava"),
    "zoe": ("Zoe (Premium)", "Zoe (Enhanced)", "Zoe"),
    "samantha": ("Samantha",),
}
DEFAULT_SPEAKER = "ava"
SPEECH_RATE = 200  # words per minute, unless the profile sets "rate" (`askr voice rate <wpm>`)
_PROFILE_PATH = os.path.expanduser("~/.config/askr/voice_profile.json")
# Re-check what's installed this often, so a voice downloaded while askr is
# running is picked up without a restart.
_RECHECK_SECS = 60.0

_chosen = ("", 0.0)  # (voice, when chosen)


def _profile() -> dict:
    try:
        with open(_PROFILE_PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def speech_rate() -> int:
    try:
        rate = int(_profile().get("rate") or SPEECH_RATE)
    except (TypeError, ValueError):
        return SPEECH_RATE
    return max(90, min(rate, 500))


def chosen_speaker() -> str:
    """The user's pick ('ava', 'zoe', 'samantha') — set with `askr voice speaker <name>`."""
    name = str(_profile().get("speaker") or "").lower()
    return name if name in VOICES else DEFAULT_SPEAKER


def installed_voices() -> set:
    out = subprocess.run(["say", "-v", "?"], capture_output=True, text=True, timeout=5).stdout
    # "Eddy (English (US)) en_US    # Hello…" — the name is everything before the locale.
    return {m.group(1) for m in re.finditer(r"^(.+?)\s+[a-z]{2,3}_[A-Z0-9]{2,3}\b", out, re.M)}


def spoken_voice() -> str:
    global _chosen
    voice, at = _chosen
    if voice and time.time() - at < _RECHECK_SECS:
        return voice
    try:
        installed = installed_voices()
    except Exception:
        return voice  # keep the last good choice; don't cache a failed lookup
    pick = chosen_speaker()
    order = [pick] + [k for k in ("ava", "zoe", "samantha") if k != pick]
    voice = next((v for k in order for v in VOICES[k] if v in installed), "")
    _chosen = (voice, time.time())
    return voice


def say_command(say_bin: str, text: str) -> list:
    """`say` argv in askr's one voice and pace."""
    cmd = [say_bin]
    voice = spoken_voice()
    if voice:
        cmd += ["-v", voice]
    return cmd + ["-r", str(speech_rate()), text]


def _say_preconditions(project_path: str = "") -> tuple[str, str]:
    """Shared gate for any spoken output: voice_notifications on, macOS, `say` on PATH.
    Returns (say_bin, "") when clear to speak, ("", reason) otherwise. `project_path`
    resolves a per-project override (askr_state/config.json) ahead of the global
    machine-level default — required for callers like the daemon whose own cwd is
    never the project being announced about."""
    if is_muted():
        return "", "askr is muted (⌘M)"
    try:
        from askr.state.config import load_voice_enabled
        if not load_voice_enabled(project_path or None):
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


def _handed_to_voice_daemon(text: str, context: dict | None) -> str:
    """
    One speaker at a time. While the voice daemon runs it is the only thing
    that talks: other processes hand their line to it (spoken in order,
    between its own replies) instead of playing `say` themselves. Found
    2026-11-25: a hook's "Done." landed on top of a voice reply and the user
    couldn't make out either. Turn-end announcements are dropped outright —
    the daemon already narrates the end of the turn it's following.
    Returns why it was handed off ('' = not handed off, speak normally).
    """
    try:
        from askr.voice import daemon, events
        pid = daemon.running_pid()
        if not pid or pid == os.getpid():
            return ""
        if str((context or {}).get("source", "")).startswith("stop._speak_session_done"):
            return "voice mode narrates turn ends"
        events.post(str((context or {}).get("session_id", "")), "announce", text)
        return "handed to the voice daemon"
    except Exception:
        return ""


def speak(text: str, voice: str = "", context: dict = None, project_path: str = "") -> tuple[bool, str]:
    """
    Speak text aloud via macOS's native `say` command.
    Gated by the user's voice_notifications preference. Returns (True, "") on
    success, (False, reason) on failure — never raises, since a broken TTS
    call should never take down a hook. `voice` selects a specific macOS
    voice (e.g. "Zarvox"); empty uses the system default. `context` is an
    optional dict (source/session_id/project_path/...) recorded alongside
    this call in voice_log.jsonl for debugging — see _log_voice_event.
    `project_path` resolves per-project config overrides; falls back to
    context["project_path"] when not passed explicitly.
    """
    if not text:
        return False, "empty text"

    project_path = project_path or (context or {}).get("project_path", "")
    say_bin, reason = _say_preconditions(project_path)
    if not say_bin:
        _log_voice_event(text, False, reason, context)
        return False, reason
    handed = _handed_to_voice_daemon(text, context)
    if handed:
        _log_voice_event(text, False, handed, context)
        return True, ""

    lock_fd = _acquire_voice_lock()
    try:
        # `voice` is ignored: everything askr says uses one voice and pace (say_command).
        subprocess.run(say_command(say_bin, humanize_for_speech(text)), timeout=30, check=False)
        _log_voice_event(text, True, "", context)
        return True, ""
    except Exception as e:
        _log_voice_event(text, False, str(e), context)
        return False, str(e)
    finally:
        _release_voice_lock(lock_fd)


def speak_signature(prefix: str, body: str, prefix_voice: str, body_voice: str, context: dict = None, project_path: str = "") -> tuple[bool, str]:
    """
    Speak a short branded prefix in one voice immediately followed by the
    detail in a second voice — askr's two-tone "sonic logo" for the
    session-done ping, distinct from any single generic TTS voice.

    Locked as a single unit so another process's announcement can never land
    between the prefix and body — that interleaving would sound just as
    garbled as two full announcements overlapping. `context`/`project_path` — see speak().
    """
    project_path = project_path or (context or {}).get("project_path", "")
    say_bin, reason = _say_preconditions(project_path)
    if not say_bin:
        _log_voice_event(f"{prefix} {body}".strip(), False, reason, context)
        return False, reason
    handed = _handed_to_voice_daemon(f"{prefix} {body}".strip(), context)
    if handed:
        _log_voice_event(f"{prefix} {body}".strip(), False, handed, context)
        return True, ""

    lock_fd = _acquire_voice_lock()
    try:
        # One voice and pace for everything (say_command); the two-voice
        # prefix/body split was dropped 2026-11-25 at the user's request.
        spoken = " ".join(humanize_for_speech(t) for t in (prefix, body) if t)
        if spoken:
            subprocess.run(say_command(say_bin, spoken), timeout=30, check=False)
        _log_voice_event(f"{prefix} {body}".strip(), True, "", context)
        return True, ""
    except Exception as e:
        _log_voice_event(f"{prefix} {body}".strip(), False, str(e), context)
        return False, str(e)
    finally:
        _release_voice_lock(lock_fd)


def announce(message: str, prefix: str = "Askr.", context: dict = None, project_path: str = "") -> tuple[bool, str]:
    """
    The single entry point every askr hook/daemon should call to speak —
    keeps all spoken output on the same voice(s) instead of some call sites
    using the configured sonic logo and others falling back to the system
    default. Honors the user's voice_mode: "dual" speaks `prefix` then
    `message` as the two-tone signature; "single" speaks `message` alone in
    one configured voice. `context`/`project_path` — see speak(). Hook
    callers rely on cwd already being the project root; the daemon (whose
    cwd is never the project it's announcing about) must pass project_path
    explicitly or via context["project_path"].
    """
    from askr.state.config import load_voice_mode, load_voice_single, load_voice_prefix, load_voice_body
    project_path = project_path or (context or {}).get("project_path", "")
    if load_voice_mode(project_path or None) == "single":
        return speak(message, voice=load_voice_single(project_path or None), context=context, project_path=project_path)
    return speak_signature(
        prefix, message,
        load_voice_prefix(project_path or None), load_voice_body(project_path or None),
        context=context, project_path=project_path,
    )
