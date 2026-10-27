"""
pre_compact must SIGKILL only the claude process that is itself compacting —
its own ancestor — never another claude session open in the same repo
(2026-10-27: PreCompact for one grid session killed a different one).
"""

from unittest.mock import patch

# Bound at import, before conftest's autouse fixture stubs the module attr.
from askr.hooks.pre_compact import _find_own_claude_pid


def _fake_ps(tree):
    """tree: {pid: (ppid, comm)} -> subprocess.run stand-in for `ps -o ppid=,comm= -p`."""
    class R:
        def __init__(self, out):
            self.stdout = out

    def run(cmd, **kwargs):
        pid = int(cmd[-1])
        if pid not in tree:
            return R("")
        ppid, comm = tree[pid]
        return R(f"  {ppid} {comm}\n")
    return run


def test_returns_claude_ancestor():
    tree = {500: (400, "/bin/sh"), 400: (300, "claude"), 300: (1, "/bin/zsh")}
    with patch("askr.hooks.pre_compact.os.getppid", return_value=500), \
         patch("askr.hooks.pre_compact.subprocess.run", side_effect=_fake_ps(tree)):
        assert _find_own_claude_pid() == 400


def test_matches_full_path_comm():
    tree = {500: (400, "/Users/x/.local/bin/claude")}
    with patch("askr.hooks.pre_compact.os.getppid", return_value=500), \
         patch("askr.hooks.pre_compact.subprocess.run", side_effect=_fake_ps(tree)):
        assert _find_own_claude_pid() == 500


def test_no_claude_ancestor_returns_none():
    tree = {500: (400, "/bin/sh"), 400: (1, "launchd")}
    with patch("askr.hooks.pre_compact.os.getppid", return_value=500), \
         patch("askr.hooks.pre_compact.subprocess.run", side_effect=_fake_ps(tree)):
        assert _find_own_claude_pid() is None


def test_ps_failure_returns_none():
    with patch("askr.hooks.pre_compact.os.getppid", return_value=500), \
         patch("askr.hooks.pre_compact.subprocess.run", side_effect=OSError("boom")):
        assert _find_own_claude_pid() is None


def test_never_consults_cwd_based_lookup():
    """The cwd fallback is what picked the wrong session — it must not be used."""
    tree = {500: (1, "/bin/sh")}
    with patch("askr.hooks.pre_compact.os.getppid", return_value=500), \
         patch("askr.hooks.pre_compact.subprocess.run", side_effect=_fake_ps(tree)), \
         patch("askr.session.lifecycle._find_session_pid", return_value=9999) as cwd_lookup:
        assert _find_own_claude_pid() is None
    cwd_lookup.assert_not_called()
