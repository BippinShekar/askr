"""
Shared pytest fixtures across the whole suite.
"""

import os
import tempfile

import pytest

from askr.utils import hook_capture


@pytest.fixture(autouse=True)
def _isolate_hook_capture_log(tmp_path, monkeypatch):
    """
    hook_capture.capture_hook_payload() is wired into every registered
    hook's main() (2026-08-11 diagnostic capture). Any test that calls a
    hook's main() — not just tests written specifically for this module —
    would otherwise append real entries to the actual
    ~/.config/askr/hook_capture.log on every suite run, diluting the one
    thing this diagnostic exists to catch: a real "you've hit your usage
    limit" event. Autouse means every test gets an isolated path with zero
    per-file changes required.
    """
    monkeypatch.setattr(hook_capture, "_CAPTURE_PATH", str(tmp_path / "hook_capture.log"))
