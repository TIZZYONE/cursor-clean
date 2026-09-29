"""Console helpers for Windows-friendly UTF-8 output."""

from __future__ import annotations

import sys


def configure_stdio() -> None:
    """Best-effort UTF-8 stdout/stderr so Chinese text works on Windows consoles."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass
