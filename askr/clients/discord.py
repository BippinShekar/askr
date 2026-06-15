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


def send_message(text: str) -> tuple[bool, str]:
    """
    Post text to the configured Discord webhook.
    Returns (True, "") on success, (False, reason) on failure.
    Truncates to Discord's 2000-char message limit.
    """
    url = os.getenv(_WEBHOOK_ENV, "").strip()
    if not url:
        return False, "ASKR_DISCORD_WEBHOOK not set"

    payload = json.dumps({"content": text[:2000]}).encode()
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
    url = os.getenv(_WEBHOOK_ENV, "").strip()
    if not url or not os.path.exists(file_path):
        return False

    boundary = uuid.uuid4().hex
    filename = os.path.basename(file_path)

    with open(file_path, "rb") as fh:
        file_data = fh.read()

    parts = []
    if caption:
        cap = caption[:2000].encode()
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
