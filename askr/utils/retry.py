"""
Retry helper for imports that race against `git pull`/`git checkout`
rewriting the target module on disk. Git's checkout uses truncate-in-place
for existing files, not write-temp-then-rename, so a concurrent import can
briefly read a partially-written file and raise ImportError even though the
module is fine a few milliseconds later.

This does not apply to askr's own state file writes (see
askr/state/writer.py's atomic write) — that's a different race between two
different write patterns.
"""

import time


def import_retry(fn, attempts: int = 3, delays=(0.05, 0.1, 0.2)):
    """Call `fn` (which performs an import + the work that needs it), retrying
    on ImportError with a short backoff. Re-raises the last ImportError if
    every attempt fails. Other exception types propagate immediately —
    only import races are worth retrying."""
    last_err = None
    for i in range(attempts):
        try:
            return fn()
        except ImportError as e:
            last_err = e
            if i < attempts - 1:
                time.sleep(delays[min(i, len(delays) - 1)])
    raise last_err
