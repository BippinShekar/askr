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


@pytest.fixture(autouse=True)
def _never_target_real_claude_process(tmp_path, monkeypatch):
    """
    pre_compact.main() SIGKILLs whatever _find_own_claude_pid() returns —
    under pytest that walk finds the live claude session running the suite
    (and the old cwd-based _find_session_pid found any claude in the repo). One under-patched
    test did exactly that on 2026-10-25 and killed the session mid-run. No test
    needs the real lookup, so resolve to None everywhere unless a test patches
    it explicitly.
    """
    from askr.hooks import pre_compact
    from askr.session import lifecycle
    monkeypatch.setattr(lifecycle, "_find_session_pid", lambda *a, **k: None)
    monkeypatch.setattr(pre_compact, "_find_own_claude_pid", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def _isolate_real_askr_side_effects(tmp_path, monkeypatch):
    """
    Under-patched tests reached _spawn_terminal_app_fallback, which detaches a
    process that 20s later opens a real Terminal.app window running
    `cd /fake/project && claude` — long after the test itself passed
    (2026-10-27). The same tests wrote notification.json, daemon.log,
    companioned_sessions.json etc. under the real ~/.config/askr, which the
    live daemon and IDE extension act on. Stub the spawner and point every
    module-level ~/.config/askr constant at tmp_path; tests that need a specific
    path still patch it themselves.
    """
    import sys
    # Ensure loaded so their paths get swept.
    from askr.hooks import pre_compact, post_tool_use  # noqa: F401
    from askr.session import checkpoint, monitor  # noqa: F401
    from askr.utils import logger  # noqa: F401
    from askr.session import lifecycle
    monkeypatch.setattr(lifecycle, "_spawn_terminal_app_fallback", lambda *a, **k: None)

    real_root = os.path.expanduser("~/.config/askr")
    sandbox = tmp_path / "config_askr"
    sandbox.mkdir()
    for name, module in list(sys.modules.items()):
        if not name.startswith("askr") or module is None:
            continue
        for attr, value in list(vars(module).items()):
            if attr.lstrip("_").isupper() and isinstance(value, str) and value.startswith(real_root):
                monkeypatch.setattr(module, attr, str(sandbox / os.path.relpath(value, real_root)))
