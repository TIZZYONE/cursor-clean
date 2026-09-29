"""ASCII progress bar."""

from __future__ import annotations

import sys
import threading
import time
from typing import Any

BAR_WIDTH = 50


class ProgressBar:
    """Single-line progress: [####----] 40.0%  12/30  label  3.2s"""

    def __init__(
        self,
        total: int | None = None,
        *,
        width: int = BAR_WIDTH,
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
        self._stop_hb = threading.Event()
        self._heartbeat: threading.Thread | None = None

    def start_heartbeat(self, interval: float = 0.5) -> None:
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
            if not force and now - self._last_draw < 0.12:
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

    def _draw(self, *, final: bool = False, ok: bool = True) -> None:
        elapsed = time.time() - self._start
        if self.total is not None:
            pct = 100.0 if final else min(99.9, 100.0 * self.current / self.total)
            if final:
                pct = 100.0
            filled = int(self.width * pct / 100.0)
            if final:
                filled = self.width
            bar = "#" * filled + "-" * (self.width - filled)
            counts = f"{self.current}/{self.total}"
            mid = f"{pct:5.1f}%  {counts}"
        else:
            pos = int(elapsed * 3) % (self.width + 6)
            chars = ["-"] * self.width
            for i in range(6):
                idx = pos - i
                if 0 <= idx < self.width:
                    chars[idx] = "#"
            bar = "".join(chars)
            mid = "working"

        flag = "" if ok else " ERR"
        line = f"\r  [{bar}] {mid} | {self.label} | {elapsed:5.0f}s{flag}"
        sys.stdout.write(line.ljust(self.width + 72))
        sys.stdout.flush()


def attach_sqlite_progress(con: Any, bar: ProgressBar, *, every: int = 2000) -> None:
    con.set_progress_handler(lambda: bar.update(force=True) or 0, every)
