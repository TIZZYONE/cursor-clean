"""ASCII progress bar — always shows a clear percentage."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any

BAR_WIDTH = 40


class ProgressBar:
    """
    Determinate:  [####----]  35%  (14/40)  聊天  12s
    Timed (VACUUM): [####----]  35%  VACUUM db=9.2G  180s
    """

    def __init__(
        self,
        total: int | None = None,
        *,
        width: int = BAR_WIDTH,
        label: str = "",
        estimate_seconds: float | None = None,
    ) -> None:
        self.total = total if total and total > 0 else None
        self.estimate_seconds = (
            float(estimate_seconds) if estimate_seconds and estimate_seconds > 0 else None
        )
        self.width = max(10, width)
        self.label = label
        self.current = 0
        self._start = time.time()
        self._last_draw = 0.0
        self._finished = False
        self._lock = threading.Lock()
        self._stop_hb = threading.Event()
        self._heartbeat: threading.Thread | None = None

    def start_heartbeat(self, interval: float = 0.4) -> None:
        if self._heartbeat and self._heartbeat.is_alive():
            return

        def _loop() -> None:
            while not self._stop_hb.wait(interval):
                self.update(force=True)

        self._heartbeat = threading.Thread(target=_loop, daemon=True)
        self._heartbeat.start()

    def stop_heartbeat(self) -> None:
        self._stop_hb.set()
        if self._heartbeat and self._heartbeat.is_alive():
            self._heartbeat.join(timeout=1.0)
        self._heartbeat = None

    def update(
        self,
        current: int | None = None,
        *,
        force: bool = False,
        label: str | None = None,
    ) -> None:
        with self._lock:
            if current is not None:
                self.current = current
            if label is not None:
                self.label = label
            now = time.time()
            if not force and now - self._last_draw < 0.1:
                return
            self._last_draw = now
            self._draw()

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

    def _percent(self, *, final: bool) -> float:
        if final:
            return 100.0
        if self.total is not None:
            return min(99.0, 100.0 * self.current / max(1, self.total))
        if self.estimate_seconds is not None:
            elapsed = time.time() - self._start
            return min(99.0, 100.0 * elapsed / self.estimate_seconds)
        return 0.0

    def _draw(self, *, final: bool = False, ok: bool = True) -> None:
        elapsed = time.time() - self._start
        pct = self._percent(final=final)
        filled = self.width if final else int(self.width * pct / 100.0)
        bar = "#" * filled + "-" * (self.width - filled)

        if self.total is not None:
            extra = f"({self.current}/{self.total})"
        else:
            extra = ""

        flag = "" if ok else " FAIL"
        # Keep line short for Windows consoles; percentage is the first signal.
        line = (
            f"\r[{bar}] {pct:5.1f}% {extra} {self.label} {elapsed:5.0f}s{flag}"
        )
        sys.stdout.write(line.ljust(max(80, self.width + 36)))
        sys.stdout.flush()


def attach_sqlite_progress(con: Any, bar: ProgressBar, *, every: int = 1500) -> None:
    def _handler() -> int:
        bar.update(force=True)
        return 0

    con.set_progress_handler(_handler, every)
