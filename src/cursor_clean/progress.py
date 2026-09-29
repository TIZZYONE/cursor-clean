"""ASCII progress bar for long-running cleanup steps."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any


DEFAULT_BAR_WIDTH = 60  # ~50% longer than the original 40


class ProgressBar:
    """In-place progress bar: [####------] 40% label 12.3s"""

    def __init__(
        self,
        total: int | None = None,
        *,
        width: int = DEFAULT_BAR_WIDTH,
        label: str = "",
        indeterminate: bool = False,
    ) -> None:
        self.total = None if indeterminate else (total if total and total > 0 else None)
        self.width = max(10, width)
        self.label = label
        self.current = 0
        self._start = time.time()
        self._last_draw = 0.0
        self._finished = False
        self._lock = threading.Lock()
        self._heartbeat: threading.Thread | None = None
        self._stop_hb = threading.Event()

    def start_heartbeat(self, interval: float = 0.5) -> None:
        """Keep redrawing elapsed time even when no sqlite callbacks fire."""
        if self._heartbeat and self._heartbeat.is_alive():
            return

        def _loop() -> None:
            while not self._stop_hb.wait(interval):
                self.update(force=True)

        self._heartbeat = threading.Thread(target=_loop, name="progress-hb", daemon=True)
        self._heartbeat.start()

    def stop_heartbeat(self) -> None:
        self._stop_hb.set()
        if self._heartbeat and self._heartbeat.is_alive():
            self._heartbeat.join(timeout=1.0)
        self._heartbeat = None

    def update(self, current: int | None = None, *, force: bool = False, label: str | None = None) -> None:
        with self._lock:
            if current is not None:
                self.current = current
            if label is not None:
                self.label = label
            now = time.time()
            if not force and (now - self._last_draw) < 0.15:
                return
            self._last_draw = now
            self._draw()

    def tick(self) -> None:
        self.current += 1
        self.update(force=False)

    def set_fraction(self, fraction: float) -> None:
        frac = max(0.0, min(0.99, float(fraction)))
        self.total = 100
        self.current = int(frac * 100)
        self.update(force=True)

    def finish(self, *, ok: bool = True) -> None:
        self.stop_heartbeat()
        with self._lock:
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
            pct = 100.0 if final else min(99.0, 100.0 * self.current / max(1, self.total))
            filled = int(self.width * pct / 100.0)
            if final:
                filled = self.width
                pct = 100.0
            bar = "#" * filled + "-" * (self.width - filled)
            suffix = f"{pct:5.1f}%"
        else:
            pos = int(elapsed * 3) % (self.width + 6)
            block = 6
            bar_chars = ["-"] * self.width
            for i in range(block):
                idx = pos - i
                if 0 <= idx < self.width:
                    bar_chars[idx] = "#"
            bar = "".join(bar_chars)
            suffix = " run "

        mark = "" if ok else " !"
        line = f"\r[{bar}] {suffix} {self.label} {elapsed:6.1f}s{mark}"
        line = line.ljust(self.width + 56)
        sys.stdout.write(line)
        sys.stdout.flush()


def attach_sqlite_progress(
    con: Any,
    bar: ProgressBar,
    *,
    every: int = 2000,
) -> None:
    """Nudge the bar from SQLite VM opcodes (supplement to heartbeat)."""

    def _handler() -> int:
        # Indeterminate / known-total: just force a redraw; heartbeat owns timing.
        bar.update(force=True)
        return 0

    con.set_progress_handler(_handler, every)
