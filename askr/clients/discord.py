import os
import ssl
import uuid
import urllib.request
import urllib.error
import json
import certifi

from askr.utils import env

env.load()

_WEBHOOK_ENV = "ASKR_DISCORD_WEBHOOK"
_MAX_LEN = 2000


def _truncate(text: str, limit: int = _MAX_LEN) -> str:
    """Trim to Discord's hard message-length limit at a word boundary, with a
    visible marker — a bare text[:limit] slice crops mid-word/mid-JSON and
    reads as garbled rather than intentionally shortened."""
    if len(text) <= limit:
        return text
    marker = "\n… [truncated]"
    cut = text[: limit - len(marker)]
    space = cut.rfind(" ")
    if space > 0:
        cut = cut[:space]
    return cut + marker


def _get_webhook_url() -> str:
    """Project config overrides global env var."""
    try:
        from askr.state.config import load_project_config
        url = load_project_config().get("discord_webhook", "").strip()
        if url:
            return url
    except Exception:
        pass
    return os.getenv(_WEBHOOK_ENV, "").strip()


def send_message(text: str) -> tuple[bool, str]:
    """
    Post text to the configured Discord webhook.
    Returns (True, "") on success, (False, reason) on failure.
    Truncates to Discord's 2000-char message limit.
    """
    url = _get_webhook_url()
    if not url:
        return False, "ASKR_DISCORD_WEBHOOK not set"

    payload = json.dumps({"content": _truncate(text)}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "askr/1.0 (session orchestration)",
        },
        method="POST",
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return resp.status in (200, 204), ""
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.reason}"
    except urllib.error.URLError as e:
        return False, f"URL error: {e.reason}"
    except OSError as e:
        return False, str(e)


def send_file(file_path: str, caption: str = "") -> bool:
    """
    Upload a file (e.g. PNG) to Discord via multipart/form-data.
    Returns True on success. Caller is responsible for deleting the file.
    """
    url = _get_webhook_url()
    if not url or not os.path.exists(file_path):
        return False

    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as fh:
        file_data = fh.read()

    parts = []
    if caption:
        cap = _truncate(caption).encode()
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="content"\r\n\r\n'.encode()
            + cap
            + b"\r\n"
        )
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: image/png\r\n\r\n'.encode()
        + file_data
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "askr/1.0 (session orchestration)",
        },
        method="POST",
    )
    ctx = ssl.create_default_context(cafile=certifi.where())
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return resp.status in (200, 204)
    except (urllib.error.URLError, OSError):
        return False
