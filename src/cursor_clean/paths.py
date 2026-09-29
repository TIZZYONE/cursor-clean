"""Resolve Cursor data directories (Windows-first)."""

from __future__ import annotations

import os
from pathlib import Path


def default_roaming_root() -> Path:
    """Return the default Cursor Roaming root on this machine."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; only Windows is supported for now.")
    return Path(appdata) / "Cursor"


def resolve_paths(data_dir: Path | None = None) -> dict[str, Path]:
    """Resolve commonly used Cursor paths under Roaming."""
    root = Path(data_dir) if data_dir else default_roaming_root()
    global_storage = root / "User" / "globalStorage"
    agent_versions = (
        global_storage
        / "anysphere.cursor-agent-worker"
        / "agent-cli"
        / ".local"
        / "share"
        / "cursor-agent"
        / "versions"
    )
    return {
        "root": root,
        "global_storage": global_storage,
        "state_db": global_storage / "state.vscdb",
        "state_db_backup": global_storage / "state.vscdb.backup",
        "agent_versions": agent_versions,
        "cached_data": root / "CachedData",
        "logs": root / "logs",
    }
