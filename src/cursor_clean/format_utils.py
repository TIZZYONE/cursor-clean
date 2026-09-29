"""Formatting helpers for human-readable sizes."""

from __future__ import annotations


def format_bytes(num: int | float) -> str:
    """Format a byte count as a short human string."""
    value = float(num)
    units = ["B", "KB", "MB", "GB", "TB"]
    for unit in units:
        if abs(value) < 1024.0 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} TB"
