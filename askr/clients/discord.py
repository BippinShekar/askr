import os
import urllib.request
import urllib.error
import json

from askr.utils import env

env.load()

_WEBHOOK_ENV = "ASKR_DISCORD_WEBHOOK"


def send_message(text: str) -> bool:
    """
    Post text to the configured Discord webhook.
    Returns True on success, False if webhook not configured or request fails.
    Truncates to Discord's 2000-char message limit.
    """
    url = os.getenv(_WEBHOOK_ENV, "").strip()
    if not url:
        return False

    payload = json.dumps({"content": text[:2000]}).encode()
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except (urllib.error.URLError, OSError):
        return False
