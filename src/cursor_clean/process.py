"""Detect whether Cursor is currently running."""

from __future__ import annotations

import subprocess
import sys


def cursor_process_count() -> int:
    """Return approximate count of running Cursor processes."""
    if sys.platform == "win32":
        try:
            completed = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Cursor.exe", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="ignore",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            return 0
        lines = [
            ln
            for ln in (completed.stdout or "").splitlines()
            if "cursor.exe" in ln.lower() and "info:" not in ln.lower()
        ]
        return len(lines)

    try:
        completed = subprocess.run(
            ["ps", "-A", "-o", "comm="],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return 0
    count = 0
    for line in completed.stdout.splitlines():
        name = (line.strip().split("/")[-1] or "").lower()
        if name in {"cursor", "cursor.exe"}:
            count += 1
    return count


def cursor_is_running() -> bool:
    """Return True if a Cursor process appears to be running."""
    return cursor_process_count() > 0
