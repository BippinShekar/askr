import platform
import shutil
import subprocess


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
        subprocess.run([say_bin, text], timeout=30, check=False)
        return True, ""
    except Exception as e:
        return False, str(e)
