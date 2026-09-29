"""ASCII progress bar for long-running cleanup steps."""

from __future__ import annotations

import sys
import time
from typing import Text


class ProgressBar:
    """In-place progress bar: [####------] 40% label 12.3s"""

    def __init__(self, total: int | None = None, *, width: int = 40, label: str = "") -> None:
        self.total = total if total and total > 0 else None
        self.width = max(10, width)
        self.label = label
        self.current = 0
        self._start = time.time()
        self._last_draw = 0.0
        self._finished = False

    def update(self, current: int | None = None, *, force: bool = False) -> None:
        if current is not None:
            self.current = current
        now = time.time()
        if not force and (now - self._last_draw) < 0.1:
            return
        self._last_draw = now
        self._draw()

    def tick(self) -> None:
        """Advance by one unit (known total) or pulse indeterminate bar."""
        self.current += 1
        self.update(force=False)

    def set_fraction(self, fraction: float) -> None:
        """Set progress to 0..1 when total is unknown (uses synthetic 100)."""
        frac = max(0.0, min(0.99, float(fraction)))
        self.total = 100
        self.current = int(frac * 100)
        self.update(force=True)

    def finish(self, *, ok: bool = True) -> None:
        if self._finished:
            return
        if self.total is not None:
            self.current = self.total
        self._draw(final=True, ok=ok)
        sys.stdout.write("\n")
        sys.stdout.flush()
        self._finished = True

    def _draw(self, *, final: bool = False, ok: bool = True) -> None:
        elapsed = time.time() - self._start
        if self.total is not None:
            pct = 100.0 if final else min(99.0, 100.0 * self.current / self.total)
            filled = int(self.width * pct / 100.0)
            if final:
                filled = self.width
                pct = 100.0
            bar = "#" * filled + "-" * (self.width - filled)
            suffix = f"{pct:5.1f}%"
        else:
            # Indeterminate: sliding block
            pos = int(elapsed * 4) % (self.width + 5)
            block = 5
            bar_chars = ["-"] * self.width
            for i in range(block):
                idx = pos - i
                if 0 <= idx < self.width:
                    bar_chars[idx] = "#"
            bar = "".join(bar_chars)
            suffix = " ..."

        mark = "" if ok else " !"
        line = f"\r[{bar}] {suffix} {self.label} {elapsed:5.1f}s{mark}"
        # Pad to clear leftovers from longer previous lines
        line = line.ljust(self.width + 48)
        sys.stdout.write(line)
        sys.stdout.flush()


def attach_sqlite_progress(
    con: Any,
    bar: ProgressBar,
    *,
    every: int = 5000,
    estimate_seconds: float | None = None,
) -> None:
    """Drive a ProgressBar from SQLite VM opcodes (works during DELETE/VACUUM)."""

    t0 = time.time()
    est = estimate_seconds if estimate_seconds and estimate_seconds > 0 else None

    def _handler() -> int:
        if est is not None:
            frac = (time.time() - t0) / est
            # Blend with tick count so bar keeps moving even if estimate is off
            bar.current = max(bar.current, int(min(99, frac * 100)))
            if bar.total is None:
                bar.total = 100
            bar.update(force=True)
        else:
            bar.tick()
        return 0  # continue

    con.set_progress_handler(_handler, every)
