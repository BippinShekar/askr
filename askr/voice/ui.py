"""
Terminal display for voice mode: transcript lines scroll, one status line
stays pinned at the bottom (state, mic level meter, live partial text).
"""

import shutil
import sys
import threading

_COLORS = {"you": "\x1b[1;36m", "askr": "\x1b[1;32m", "claude": "\x1b[35m",
           "ignored": "\x1b[2m", "info": "\x1b[33m", "error": "\x1b[1;31m"}
_RESET = "\x1b[0m"


def meter(level: float, threshold: float, width: int = 12) -> str:
    """Log-scaled mic bar; the bracket marks where speech detection starts."""
    import math
    def pos(x):
        x = max(x, 1e-4)
        return int(round((math.log10(x) + 4) / 3.5 * width))  # 1e-4 .. ~0.3
    n, t = min(pos(level), width), min(pos(threshold), width - 1)
    return "".join("|" if i == t else ("▮" if i < n else "·") for i in range(width))


class Display:
    def __init__(self, stream=None):
        self.stream = stream or sys.stdout
        self._lock = threading.Lock()
        self._status = ""

    def _width(self) -> int:
        return shutil.get_terminal_size((100, 20)).columns

    def _draw_status(self):
        self.stream.write("\r\x1b[K" + self._status[: self._width() - 1])
        self.stream.flush()

    def line(self, kind: str, text: str):
        with self._lock:
            color = _COLORS.get(kind, "")
            label = "" if kind in ("info", "error", "ignored") else f"{kind}: "
            self.stream.write("\r\x1b[K" + f"{color}{label}{text}{_RESET}\n")
            self._draw_status()

    def status(self, state: str, level: float = 0.0, threshold: float = 0.0, partial: str = ""):
        with self._lock:
            bar = meter(level, threshold) if threshold else ""
            self._status = f"● {state:<12} {bar}  {partial}".rstrip()
            self._draw_status()
